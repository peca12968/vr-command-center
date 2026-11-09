package com.vrcommand.udpprobe;

import android.app.Activity;
import android.app.Instrumentation;
import android.os.Bundle;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;

public final class ProbeInstrumentation extends Instrumentation {
    private Bundle arguments;

    @Override public void onCreate(Bundle args) {
        arguments = args;
        start();
    }

    @Override public void onStart() {
        Probe.Result result = probe();
        Bundle output = new Bundle();
        output.putString("probeReport", result.json);
        finish(Activity.RESULT_OK, output);
    }

    private Probe.Result probe() {
        String keyName = arguments == null ? null : arguments.getString("keyName");
        if (keyName == null || !keyName.matches("udp-[0-9a-f]{32}\\.key")) return Probe.failed("arguments");
        Path keyPath = getTargetContext().getFilesDir().toPath().resolve(keyName);
        byte[] key = null;
        try {
            try {
                key = Probe.readKey(keyPath);
            } finally {
                Files.deleteIfExists(keyPath);
            }
            return Probe.run(key, arguments.getString("localAddress"), arguments.getString("peerAddress"),
                    arguments.getString("port"), arguments.getString("count"), arguments.getString("timeoutMs"));
        } catch (IOException | SecurityException error) {
            return Probe.failed("key");
        } finally {
            if (key != null) Arrays.fill(key, (byte) 0);
        }
    }
}
