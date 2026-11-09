package com.vrcommand.udpprobe;

import java.io.IOException;
import java.io.InputStream;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.PortUnreachableException;
import java.net.SocketTimeoutException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.security.GeneralSecurityException;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Base64;
import java.util.Collections;
import java.util.List;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

final class Probe {
    private static final String HEX = "0123456789abcdef";
    private static final int PACKET_BYTES = 105;

    static final class Result {
        final boolean complete;
        final String json;

        Result(boolean complete, String json) {
            this.complete = complete;
            this.json = json;
        }
    }

    private Probe() {}

    static Result failed(String step) {
        return new Result(false, "{\"version\":1,\"stage\":\"failed\",\"step\":\"" + step + "\",\"complete\":false}");
    }

    static byte[] readKey(Path path) throws IOException {
        byte[] buffer = new byte[47];
        int size = 0;
        try (InputStream input = Files.newInputStream(path)) {
            while (size < buffer.length) {
                int read = input.read(buffer, size, buffer.length - size);
                if (read < 0) break;
                size += read;
            }
        }
        if (size < 44 || size > 46) throw new IOException("Invalid key length");
        return Arrays.copyOf(buffer, size);
    }

    static Result run(byte[] encodedKey, String localText, String peerText, String portText, String countText, String timeoutText) {
        String step = "key";
        byte[] key = null;
        try {
            String encoded = new String(encodedKey, StandardCharsets.US_ASCII).trim();
            key = Base64.getDecoder().decode(encoded);
            if (key.length != 32 || !Base64.getEncoder().encodeToString(key).equals(encoded)) return failed(step);
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(key, "HmacSHA256"));

            step = "address";
            InetAddress local = address(localText);
            InetAddress peer = address(peerText);
            int port = number(portText, 1024, 65535);
            int count = number(countText, 1, 20);
            int timeout = number(timeoutText, 200, 3000);
            InetSocketAddress endpoint = new InetSocketAddress(peer, port);

            step = "bind";
            try (DatagramSocket socket = new DatagramSocket(new InetSocketAddress(local, 0))) {
                socket.connect(endpoint);
                step = "exchange";
                return exchange(socket, mac, localText, peerText, port, count, timeout);
            }
        } catch (IOException | GeneralSecurityException | IllegalArgumentException | SecurityException error) {
            return failed(step);
        } finally {
            Arrays.fill(encodedKey, (byte) 0);
            if (key != null) Arrays.fill(key, (byte) 0);
        }
    }

    private static int number(String value, int min, int max) {
        if (value == null || !value.matches("[1-9][0-9]{0,4}")) throw new IllegalArgumentException("Invalid number");
        int parsed = Integer.parseInt(value);
        if (parsed < min || parsed > max) throw new IllegalArgumentException("Number outside bounds");
        return parsed;
    }

    private static InetAddress address(String text) throws IOException {
        if (text == null || !text.matches("(?:0|[1-9][0-9]{0,2})(?:\\.(?:0|[1-9][0-9]{0,2})){3}"))
            throw new IllegalArgumentException("Invalid IPv4");
        String[] parts = text.split("\\.");
        byte[] octets = new byte[4];
        for (int i = 0; i < octets.length; i++) {
            int value = Integer.parseInt(parts[i]);
            if (value > 255) throw new IllegalArgumentException("Invalid IPv4");
            octets[i] = (byte) value;
        }
        int a = Byte.toUnsignedInt(octets[0]), b = Byte.toUnsignedInt(octets[1]);
        if (!(a == 10 || a == 127 || (a == 172 && b >= 16 && b <= 31) || (a == 192 && b == 168)))
            throw new IllegalArgumentException("Expected a private or loopback IPv4");
        return InetAddress.getByAddress(octets);
    }

    private static String hex(byte[] bytes) {
        StringBuilder result = new StringBuilder(bytes.length * 2);
        for (byte value : bytes) result.append(HEX.charAt((value & 255) >>> 4)).append(HEX.charAt(value & 15));
        return result.toString();
    }

    private static byte[] packet(Mac mac, char kind, String nonce) {
        String prefix = "VRLAN1" + kind + ":" + nonce;
        return (prefix + ":" + hex(mac.doFinal(prefix.getBytes(StandardCharsets.US_ASCII)))).getBytes(StandardCharsets.US_ASCII);
    }

    private static Result exchange(DatagramSocket socket, Mac mac, String local, String peer, int port, int count, int timeout)
            throws IOException, GeneralSecurityException {
        SecureRandom random = new SecureRandom();
        List<String> nonces = new ArrayList<>();
        List<String> samples = new ArrayList<>();
        for (int sample = 1; sample <= count; sample++) {
            byte[] challenge = new byte[16];
            random.nextBytes(challenge);
            String nonce = hex(challenge);
            byte[] request = packet(mac, 'Q', nonce);
            byte[] expected = packet(mac, 'R', nonce);
            Double rtt = sendAndWait(socket, request, expected, timeout);
            if (rtt != null) nonces.add(nonce);
            samples.add("{\"sample\":" + sample + ",\"roundTripMs\":" + rtt + "}");
        }
        Collections.sort(nonces);
        String material = "VRLAN1\n" + peer + "\n" + local + "\n" + port + "\n" + String.join("\n", nonces);
        String digest = nonces.isEmpty() ? "null" : "\"" + hex(MessageDigest.getInstance("SHA-256")
                .digest(material.getBytes(StandardCharsets.US_ASCII))) + "\"";
        boolean complete = nonces.size() == count;
        String json = "{\"version\":1,\"stage\":\"finished\",\"mode\":\"probe\",\"localAddress\":\"" + local
                + "\",\"peerAddress\":\"" + peer + "\",\"port\":" + port + ",\"requested\":" + count
                + ",\"matched\":" + nonces.size() + ",\"samples\":[" + String.join(",", samples) + "]"
                + ",\"exchangeSha256\":" + digest + ",\"complete\":" + complete + ",\"scope\":\"authenticated-udp-only\""
                + ",\"completedAtUtc\":\"" + Instant.now().truncatedTo(ChronoUnit.MILLIS) + "\"}";
        return new Result(complete, json);
    }

    private static Double sendAndWait(DatagramSocket socket, byte[] request, byte[] expected, int timeout) throws IOException {
        // The connected socket accepts only the configured peer address and game port.
        DatagramPacket response = new DatagramPacket(new byte[PACKET_BYTES + 1], PACKET_BYTES + 1);
        long start = System.nanoTime(), limit = timeout * 1_000_000L;
        try {
            socket.send(new DatagramPacket(request, request.length, socket.getRemoteSocketAddress()));
            long remaining;
            while ((remaining = limit - (System.nanoTime() - start)) > 0) {
                socket.setSoTimeout((int) ((remaining + 999_999) / 1_000_000));
                response.setLength(response.getData().length);
                socket.receive(response);
                long elapsed = System.nanoTime() - start;
                if (elapsed > limit) return null;
                if (response.getLength() == expected.length
                        && MessageDigest.isEqual(expected, Arrays.copyOf(response.getData(), expected.length)))
                    return Math.round(elapsed / 1_000.0) / 1_000.0;
            }
        } catch (SocketTimeoutException | PortUnreachableException missed) {
            return null;
        }
        return null;
    }

    // Desktop entry point for testing the same UDP implementation used by Android.
    public static void main(String[] args) {
        Result result = failed("arguments");
        if (args.length == 6) {
            try {
                result = run(readKey(Paths.get(args[0])), args[1], args[2], args[3], args[4], args[5]);
            } catch (IOException error) {
                result = failed("key");
            }
        }
        System.out.println(result.json);
        System.exit(result.complete ? 0 : 1);
    }
}
