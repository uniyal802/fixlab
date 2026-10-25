import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from auth import AuthenticationError, resolve_identity, validate_configuration


class AuthTests(unittest.TestCase):
    def test_local_mode_keeps_single_user_identity(self):
        with patch.dict(os.environ, {'FIXLAB_AUTH_MODE':'local'}, clear=False):
            self.assertEqual(resolve_identity({})['owner_id'],'local')

    def test_hosted_mode_requires_valid_bearer_token(self):
        config=json.dumps([{'token':'a'*32,'owner_id':'account-1','quotas':{'active_jobs':3}}])
        with patch.dict(os.environ, {'FIXLAB_AUTH_MODE':'required','FIXLAB_AUTH_TOKENS':config,'FIXLAB_RETENTION_DAYS':'30'}, clear=False):
            validate_configuration()
            with self.assertRaises(AuthenticationError):resolve_identity({})
            with self.assertRaises(AuthenticationError):resolve_identity({'Authorization':'Bearer wrong-token'})
            identity=resolve_identity({'Authorization':'Bearer '+'a'*32})
            self.assertEqual(identity,{'owner_id':'account-1','quotas':{'active_jobs':3}})

    def test_hosted_mode_requires_tokens_and_retention(self):
        with patch.dict(os.environ, {'FIXLAB_AUTH_MODE':'required','FIXLAB_AUTH_TOKENS':'[]','FIXLAB_RETENTION_DAYS':'0'}, clear=False):
            with self.assertRaisesRegex(RuntimeError,'at least one'):
                validate_configuration()


if __name__ == '__main__':
    unittest.main()
