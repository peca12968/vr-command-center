"""A loopback-only simulated device for VR Command hardware rehearsals."""
import argparse
import json
import os
from pathlib import Path
import socket
import struct
import sys
import time
import uuid

# Keep the extracted simulator package byte-for-byte verifiable after running the peer.
sys.dont_write_bytecode = True
from windows_firewall import WindowsFirewallLaunchError, require_silent_windows_launch


def send(sock, value):
    body = json.dumps(value, separators=(',', ':')).encode()
    sock.sendall(struct.pack('>I', len(body)) + body)


def receive(stream):
    header = stream.read(4)
    if not header:
        return None
    size, = struct.unpack('>I', header)
    if not 0 < size <= 32 * 1024:
        raise ValueError('Invalid mock frame size')
    return json.loads(stream.read(size))


def emit(value):
    print(json.dumps(value), flush=True)


def observe_close(sock, stream, frame, received):
    sock.settimeout(2)
    transport = 'eof'
    try:
        if stream.read(1) != b'':
            raise ValueError('Expected the gateway to close its connection')
    except (ConnectionResetError, ConnectionAbortedError):
        transport = 'reset'
    except TimeoutError:
        transport = 'still-open'
    emit({'kind':'closed' if transport != 'still-open' else 'still-open', 'connectionId':frame['connectionId'],
          'batchId':frame.get('batchId'), 'transport':transport,
          'elapsedMilliseconds':round((time.monotonic()-received)*1000, 2)})


def exchange(sock, manual, assigned_room):
    connection = None
    room = None
    with sock.makefile('rb') as stream:
        while frame := receive(stream):
            first = connection is None
            if frame['version'] != 1 or frame['mode'] != 'simulation' or frame['kind'] != ('hello' if first else 'feedback'):
                raise ValueError('Invalid mock frame')
            frame_room = frame['roomId']
            if type(frame_room) is not int or not 1 <= frame_room <= 5:
                raise ValueError('Invalid mock room')
            if first:
                if assigned_room is not None and frame_room != assigned_room:
                    emit({'kind':'room-rejected', 'roomId':frame_room, 'expectedRoomId':assigned_room})
                    return
                connection = frame['connectionId']
                if not isinstance(connection, str) or str(uuid.UUID(connection)) != connection:
                    raise ValueError('Invalid mock connection')
                room = frame_room
            elif frame_room != room or frame['connectionId'] != connection:
                raise ValueError('Feedback does not belong to this mock connection')
            received = time.monotonic()
            emit(frame)
            action = sys.stdin.readline().strip() if manual else 'ack'
            if action == 'timeout':
                time.sleep(1.05)
                return
            if action == 'drop':
                return
            if action == 'observe-close':
                observe_close(sock, stream, frame, received)
                return
            if action not in ('ack', 'wrong') and not (first and action == 'ready-observe-close'):
                raise ValueError('Use ack, wrong, drop, timeout, observe-close or ready-observe-close during hello')
            reply = {'version':1, 'kind':'ready' if first else 'ack', 'connectionId':frame['connectionId']}
            if not first:
                reply['batchId'] = str(uuid.uuid4()) if action == 'wrong' else frame['batchId']
            send(sock, reply)
            if action == 'ready-observe-close':
                observe_close(sock, stream, frame, received)
                return


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=0, help='Loopback TCP port (0 chooses a free port)')
    parser.add_argument('--room', type=int, choices=range(1,6), help='Accept handshakes for this room only')
    parser.add_argument('--manual', action='store_true', help='Read a simulated acknowledgement instruction from stdin')
    args = parser.parse_args()
    if args.port != 0 and not 1024 <= args.port <= 65535:
        parser.error('Use 0 or a port in 1024–65535')
    directory = os.environ.get('VR_COMMAND_HARDWARE_IPC_DIRECTORY')
    if directory is None:
        try:
            require_silent_windows_launch(sys.executable)
        except WindowsFirewallLaunchError as error:
            parser.exit(2, f'{error}\n')
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', args.port))
            serve(listener, listener.getsockname()[1], args)
        return

    root = Path(directory)
    if not root.is_absolute() or not root.is_dir() or not args.port:
        parser.error('Local IPC requires an existing absolute directory and an explicit mock port number')
    path = root / f'mock-{args.port}.sock'
    accept = accept_connection
    if os.name == 'nt':
        from windows_ipc_api import accept_unix, bind_unix, unix_address
        accept = accept_unix
    with socket.socket(getattr(socket, 'AF_UNIX', 1), socket.SOCK_STREAM) as listener:
        if os.name == 'nt':
            bind_unix(listener, unix_address(path))
        else:
            listener.bind(str(path))
        try:
            serve(listener, args.port, args, accept)
        finally:
            path.unlink(missing_ok=True)


def accept_connection(listener):
    return listener.accept()[0]


def serve(listener, port, args, accept=accept_connection):
    listener.listen()
    emit({'kind':'listening', 'port':port})
    while True:
        with accept(listener) as sock:
            sock.settimeout(125)
            try:
                exchange(sock, args.manual, args.room)
            except (KeyError, TypeError, ValueError, OSError, struct.error):
                continue


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
