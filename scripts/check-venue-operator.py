"""Check the HTTPS control console and one operator's room access from this workstation."""
import argparse
from contextlib import closing
import getpass
import hashlib
import hmac
import http.client
import json
import os
from pathlib import Path
import re
import ssl
import sys
from urllib.parse import urlsplit
import warnings


ROLES = {'master': None, **{f'room{i}': i for i in range(1, 6)}}
KEY_ENV = 'VR_COMMAND_OPERATOR_KEY'
BODY_LIMIT = 128 * 1024


class CheckFailed(Exception):
    pass


def endpoint(origin):
    try:
        parsed = urlsplit(origin)
        host = parsed.hostname
        port = parsed.port if parsed.port is not None else 443
    except ValueError:
        raise CheckFailed('invalid-https-origin') from None
    if (not host or not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?', host)
            or not 1 <= port <= 65535 or not re.fullmatch(
                rf'https://{re.escape(host)}(?::{port})?/?', origin, flags=re.ASCII | re.IGNORECASE)):
        raise CheckFailed('invalid-https-origin')
    return host, port


def tls_context(ca_file):
    # PROTOCOL_TLS_CLIENT checks the certificate chain and host name. It also avoids
    # enabling TLS session key logging from the environment.
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    if ca_file is None:
        context.load_default_certs()
    else:
        context.load_verify_locations(cafile=ca_file)
    return context


def read_route(host, port, context, fingerprint, path, status, content_type=None, token=None):
    try:
        with closing(http.client.HTTPSConnection(host, port, timeout=5, context=context)) as connection:
            connection.connect()
            peer = connection.sock.getpeercert(binary_form=True)
            if not peer or not hmac.compare_digest(hashlib.sha256(peer).hexdigest(), fingerprint):
                raise CheckFailed('certificate-fingerprint-mismatch')

            headers = {'Cache-Control': 'no-cache, no-store', 'Connection': 'close'}
            if token is not None:
                headers['Authorization'] = f'Bearer {token}'
            connection.request('GET', path, headers=headers)
            with connection.getresponse() as response:
                if response.status != status:
                    raise CheckFailed(f'unexpected-http-{response.status}')
                if status == 401:
                    if response.getheader('WWW-Authenticate', '').lower() != 'bearer':
                        raise CheckFailed('missing-bearer-challenge')
                    return None
                received_type = response.getheader('Content-Type', '').split(';', 1)[0].strip().lower()
                if received_type != content_type:
                    raise CheckFailed('unexpected-content-type')
                data = response.read(BODY_LIMIT + 1)
                if len(data) > BODY_LIMIT or response.length not in (None, 0):
                    raise CheckFailed('invalid-response-length')
                if content_type == 'application/json':
                    return json.loads(data)
                return data
    except ssl.SSLCertVerificationError:
        raise CheckFailed('certificate-trust-or-hostname-failed') from None
    except (OSError, http.client.HTTPException):
        raise CheckFailed('connection-or-response-failed') from None
    except (ValueError, RecursionError):
        raise CheckFailed('invalid-response') from None


def operator_key():
    key = os.environ.get(KEY_ENV)
    if key is None:
        with warnings.catch_warnings():
            warnings.simplefilter('error', getpass.GetPassWarning)
            try:
                key = getpass.getpass('Operator key (hidden): ')
            except (EOFError, getpass.GetPassWarning):
                raise CheckFailed('operator-key-input-unavailable') from None
    if not re.fullmatch(r'[\x21-\x7e]{1,512}', key):
        raise CheckFailed('invalid-operator-key')
    return key


def check(host, port, context, fingerprint, role):
    if not re.fullmatch(r'[0-9a-fA-F]{64}', fingerprint):
        raise CheckFailed('invalid-certificate-fingerprint')
    fingerprint = fingerprint.lower()
    report = {'schemaVersion': 1, 'complete': False, 'origin': f'https://{host}:{port}',
              'expectedCertificateSha256': fingerprint, 'expectedRole': role, 'checks': []}
    room = ROLES[role]
    stage = 'console'

    def read(path, status=200, content_type='application/json', token=None):
        return read_route(host, port, context, fingerprint, path, status, content_type, token)

    try:
        console = read('/console/', content_type='text/html')
        if b'id="login-form"' not in console:
            raise CheckFailed('control-console-marker-missing')
        report['checks'].append(stage)
        stage = 'anonymous-identity'
        read('/api/me', status=401)
        report['checks'].append(stage)
        stage = 'anonymous-rooms'
        read('/api/rooms', status=401)
        report['checks'].append(stage)

        stage = 'operator-identity'
        key = operator_key()
        identity = read('/api/me', token=key)
        expected = 'Master' if room is None else 'RoomController'
        if (not isinstance(identity, dict) or identity.get('role') != expected or 'roomId' not in identity
                or type(identity['roomId']) is not type(room) or identity['roomId'] != room):
            raise CheckFailed('operator-role-or-room-mismatch')
        report['checks'].append(stage)

        stage = 'visible-rooms'
        rooms = read('/api/rooms', token=key)
        expected_rooms = [1, 2, 3, 4, 5] if room is None else [room]
        if (not isinstance(rooms, list) or len(rooms) != len(expected_rooms) or any(
                not isinstance(row, dict) or type(row.get('id')) is not int
                or type(row.get('capacity')) is not int or row['capacity'] != 5 for row in rooms)
                or sorted(row['id'] for row in rooms) != expected_rooms):
            raise CheckFailed('visible-rooms-or-capacity-mismatch')
        report['checks'].append(stage)
        report.update(complete=True, roomIds=expected_rooms)
    except CheckFailed as exc:
        report.update(failedCheck=stage, error=str(exc))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('origin', help='HTTPS origin with DNS name or IPv4 and optional port')
    parser.add_argument('--role', required=True, choices=ROLES)
    parser.add_argument('--certificate-sha256', required=True, help='Expected SHA-256 of the leaf certificate DER, from the administrator')
    parser.add_argument('--ca-file', type=Path, help='Explicit trusted PEM CA bundle for this check only')
    args = parser.parse_args()
    try:
        host, port = endpoint(args.origin)
        context = tls_context(args.ca_file)
        report = check(host, port, context, args.certificate_sha256, args.role)
    except CheckFailed as exc:
        report = {'schemaVersion': 1, 'complete': False, 'failedCheck': 'configuration', 'error': str(exc)}
    except (OSError, ValueError):
        report = {'schemaVersion': 1, 'complete': False, 'failedCheck': 'configuration', 'error': 'trust-store-unavailable'}
    print(json.dumps(report, indent=2))
    return 0 if report['complete'] else 1


if __name__ == '__main__':
    sys.exit(main())
