"""API identity resolution for local single-user and configured hosted modes.

Hosted mode accepts opaque bearer tokens mapped to owners by deployment config.
The tokens are never persisted; deployments must keep this config out of source
control and deliver it through their secret manager.
"""
import hashlib
import hmac
import json
import os
import re

LOCAL_OWNER = 'local'
OWNER_PATTERN = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:@-]{0,127}$')


class AuthenticationError(Exception):
    pass


def auth_mode():
    mode = os.getenv('FIXLAB_AUTH_MODE', 'local').strip().lower()
    if mode not in ('local', 'required'):
        raise RuntimeError('FIXLAB_AUTH_MODE must be local or required')
    return mode


def _token_records():
    try:
        records = json.loads(os.getenv('FIXLAB_AUTH_TOKENS', '[]'))
    except json.JSONDecodeError as exc:
        raise RuntimeError('FIXLAB_AUTH_TOKENS must contain a JSON array') from exc
    if not isinstance(records, list):
        raise RuntimeError('FIXLAB_AUTH_TOKENS must contain a JSON array')
    for record in records:
        if (not isinstance(record, dict) or not isinstance(record.get('token'), str)
                or len(record['token']) < 24 or not isinstance(record.get('owner_id'), str)
                or not OWNER_PATTERN.fullmatch(record['owner_id'])):
            raise RuntimeError('Each auth token record needs a 24+ character token and valid owner_id')
        quotas = record.get('quotas', {})
        if not isinstance(quotas, dict):
            raise RuntimeError('Token quotas must be a JSON object')
        if set(quotas) - {'active_jobs', 'request_bytes', 'storage_bytes'}:
            raise RuntimeError('Unsupported quota key in auth token record')
        yield record


def validate_configuration():
    if auth_mode() == 'local':
        return
    records = list(_token_records())
    if not records:
        raise RuntimeError('Hosted auth mode requires at least one configured bearer token')
    tokens = set()
    for record in records:
        if record['token'] in tokens:
            raise RuntimeError('Auth tokens must be unique')
        tokens.add(record['token'])
        for key, maximum in (('active_jobs', 1000), ('request_bytes', 10_000_000), ('storage_bytes', 1_000_000_000_000)):
            if key in record.get('quotas', {}):
                try: value = int(record['quotas'][key])
                except (TypeError, ValueError) as exc: raise RuntimeError('Invalid quota: ' + key) from exc
                if not 1 <= value <= maximum: raise RuntimeError('Invalid quota: ' + key)
    if auth_mode() == 'required':
        try: retention = int(os.getenv('FIXLAB_RETENTION_DAYS', '0'))
        except ValueError as exc: raise RuntimeError('FIXLAB_RETENTION_DAYS must be a positive integer in hosted mode') from exc
        if not 1 <= retention <= 36500:
            raise RuntimeError('FIXLAB_RETENTION_DAYS must be a positive integer in hosted mode')


def resolve_identity(headers):
    if auth_mode() == 'local':
        return {'owner_id': LOCAL_OWNER, 'quotas': {}}
    authorization = headers.get('Authorization', '')
    scheme, _, supplied = authorization.partition(' ')
    if scheme.lower() != 'bearer' or not supplied:
        raise AuthenticationError('Authentication required')
    supplied_digest = hashlib.sha256(supplied.encode()).digest()
    matched = None
    for record in _token_records():
        candidate_digest = hashlib.sha256(record['token'].encode()).digest()
        if hmac.compare_digest(supplied_digest, candidate_digest):
            matched = record
    if matched is None:
        raise AuthenticationError('Invalid bearer token')
    return {'owner_id': matched['owner_id'], 'quotas': matched.get('quotas', {})}
