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
from uuid import UUID
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


def read_route(host, port, context, fingerprint, path, status, content_type=None, token=None, *, body=None):
    try:
        with closing(http.client.HTTPSConnection(host, port, timeout=5, context=context)) as connection:
            connection.connect()
            peer = connection.sock.getpeercert(binary_form=True)
            if not peer or not hmac.compare_digest(hashlib.sha256(peer).hexdigest(), fingerprint):
                raise CheckFailed('certificate-fingerprint-mismatch')

            headers = {'Cache-Control': 'no-cache, no-store', 'Connection': 'close'}
            if token is not None:
                headers['Authorization'] = f'Bearer {token}'
            if body is None:
                connection.request('GET', path, headers=headers)
            else:
                headers['Content-Type'] = 'application/json'
                connection.request('POST', path, body=json.dumps(body).encode(), headers=headers)
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


def require_witness(value, challenge, role):
    fields = {'version', 'challenge', 'workstation', 'source', 'listener', 'port', 'observedAtUnixSeconds', 'signature'}
    if (not isinstance(value, dict) or value.keys() != fields or type(value['version']) is not int or value['version'] != 1
            or value['challenge'] != challenge or type(value['workstation']) is not int or value['workstation'] != (ROLES[role] or 0)
            or not isinstance(value['source'], str) or not isinstance(value['listener'], str)
            or type(value['port']) is not int or not 1 <= value['port'] <= 65535 or type(value['observedAtUnixSeconds']) is not int
            or not isinstance(value['signature'], str) or not re.fullmatch(r'[0-9a-f]{64}', value['signature'])):
        raise CheckFailed('workstation-witness-does-not-match-role-or-challenge')
    return value


def check(host, port, context, fingerprint, role, challenge=None):
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
        if challenge is not None:
            stage = 'workstation-witness'
            witness = read('/api/operator-network/witness?challenge=' + challenge, token=key)
            report['networkWitness'] = require_witness(witness, challenge, role)
            report['checks'].append(stage)
        report.update(complete=True, roomIds=expected_rooms)
    except CheckFailed as exc:
        report.update(failedCheck=stage, error=str(exc))
    return report


def local_json(path):
    try:
        with path.open('rb') as source:
            data = source.read(BODY_LIMIT + 1)
        if len(data) <= BODY_LIMIT:
            return json.loads(data.decode('utf-8-sig'))
    except (OSError, ValueError, RecursionError):
        pass
    raise CheckFailed('invalid-workstation-json-file')


def verify_workstations(host, port, context, fingerprint, challenge, inventory_file, report_files):
    if not re.fullmatch(r'[0-9a-fA-F]{64}', fingerprint):
        raise CheckFailed('invalid-certificate-fingerprint')
    fingerprint = fingerprint.lower()
    origin = f'https://{host}:{port}'
    inventory = local_json(inventory_file)
    if (not isinstance(inventory, dict) or inventory.keys() != {'masterAddress', 'roomAddresses'}
            or not isinstance(inventory['masterAddress'], str) or not isinstance(inventory['roomAddresses'], list)
            or len(inventory['roomAddresses']) != 5 or any(not isinstance(item, str) for item in inventory['roomAddresses'])):
        raise CheckFailed('invalid-workstation-inventory')
    witnesses = {}
    for path in report_files:
        report = local_json(path)
        role = report.get('expectedRole') if isinstance(report, dict) else None
        if (not isinstance(role, str) or role not in ROLES or role in witnesses or report.get('complete') is not True
                or report.get('origin') != origin or report.get('expectedCertificateSha256') != fingerprint):
            raise CheckFailed('workstation-report-does-not-match-venue-or-role')
        witnesses[role] = require_witness(report.get('networkWitness'), challenge, role)
    if witnesses.keys() != ROLES.keys():
        raise CheckFailed('require-master-and-five-room-reports')
    read_route(host, port, context, fingerprint, '/api/me', 401)
    value = read_route(host, port, context, fingerprint, '/api/operator-network/verify', 200, 'application/json',
                       operator_key(), body={'challenge': challenge, 'inventory': inventory, 'witnesses': list(witnesses.values())})
    expected = [inventory['masterAddress'], *inventory['roomAddresses']]
    if (not isinstance(value, dict) or value.get('challenge') != challenge or value.get('workstationAddresses') != expected
            or any((w['listener'], w['port']) != (value.get('listener'), value.get('port')) for w in witnesses.values())):
        raise CheckFailed('invalid-venue-verification-response')
    return {'schemaVersion': 1, 'complete': True, 'origin': origin, 'challenge': challenge,
            'managementAddress': value.get('listener'), 'managementPort': value.get('port'), 'workstationAddresses': expected}


def challenge_value(value):
    try:
        parsed = UUID(value)
        if parsed.int and str(parsed) == value:
            return value
    except ValueError:
        pass
    raise argparse.ArgumentTypeError('Use a nonempty lower-case UUID.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('origin', help='HTTPS origin with DNS name or IPv4 and optional port')
    parser.add_argument('--role', required=True, choices=ROLES)
    parser.add_argument('--certificate-sha256', required=True, help='Expected SHA-256 of the leaf certificate DER, from the administrator')
    parser.add_argument('--ca-file', type=Path, help='Explicit trusted PEM CA bundle for this check only')
    parser.add_argument('--venue-challenge', type=challenge_value, help='Shared UUID for the six direct venue workstation checks')
    parser.add_argument('--verify-workstations', nargs=7, type=Path, metavar='FILE',
                        help='Verify the inventory JSON followed by all six signed workstation reports')
    args = parser.parse_args()
    if args.verify_workstations and (args.role != 'master' or not args.venue_challenge):
        parser.error('--verify-workstations requires --role master and --venue-challenge.')
    try:
        host, port = endpoint(args.origin)
        context = tls_context(args.ca_file)
        if args.verify_workstations:
            inventory, *reports = args.verify_workstations
            report = verify_workstations(host, port, context, args.certificate_sha256, args.venue_challenge, inventory, reports)
        else:
            report = check(host, port, context, args.certificate_sha256, args.role, args.venue_challenge)
    except CheckFailed as exc:
        report = {'schemaVersion': 1, 'complete': False, 'failedCheck': 'workstations' if args.verify_workstations else 'configuration', 'error': str(exc)}
    except (OSError, ValueError):
        report = {'schemaVersion': 1, 'complete': False, 'failedCheck': 'configuration', 'error': 'trust-store-unavailable'}
    print(json.dumps(report, indent=2))
    return 0 if report['complete'] else 1


if __name__ == '__main__':
    sys.exit(main())
