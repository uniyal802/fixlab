import json
import sys
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from pathlib import Path
from unittest.mock import patch
from http.server import ThreadingHTTPServer
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
import core
from server import Handler

class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.http=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True)
        cls.thread.start()
        cls.base='http://127.0.0.1:'+str(cls.http.server_port)
    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown();cls.http.server_close();cls.thread.join()
    def request(self,path,data=None,origin=None,token=None):
        headers={'Content-Type':'application/json'}
        if origin: headers['Origin']=origin
        if token: headers['Authorization']='Bearer '+token
        req=urllib.request.Request(self.base+path,data=json.dumps(data).encode() if data is not None else None,headers=headers)
        with urllib.request.urlopen(req) as response:return json.load(response)
    def expect_http(self,code,path,data=None,token=None):
        with self.assertRaises(urllib.error.HTTPError) as context:self.request(path,data,token=token)
        self.assertEqual(context.exception.code,code)
    def test_cross_origin_write_rejected(self):
        with self.assertRaises(urllib.error.HTTPError) as context:self.request('/api/analyze',{'code':'pass'},'https://example.com')
        self.assertEqual(context.exception.code,403)
    def test_analysis_returns_durable_job_and_cancel_endpoint(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(core,'DB',Path(tmp)/'db'):
            accepted=self.request('/api/analyze',{'code':'def f(): return 1','error':''})
            self.assertEqual(accepted['state'],'queued')
            self.assertEqual(self.request('/api/jobs/'+accepted['job_id'])['state'],'queued')
            self.assertEqual(self.request('/api/jobs/'+accepted['job_id']+'/cancel',{})['state'],'cancelled')
    def test_hosted_auth_rejects_missing_and_invalid_tokens(self):
        config=json.dumps([{'token':'a'*32,'owner_id':'account-a'},{'token':'b'*32,'owner_id':'account-b'}])
        with patch.dict('os.environ',{'FIXLAB_AUTH_MODE':'required','FIXLAB_AUTH_TOKENS':config,'FIXLAB_RETENTION_DAYS':'30'}):
            self.expect_http(401,'/api/health')
            self.expect_http(401,'/api/health',token='wrong')
            self.assertEqual(self.request('/api/sessions',token='a'*32),[])
    def test_sessions_jobs_and_writes_are_owner_scoped(self):
        token_a='a'*32;token_b='b'*32
        config=json.dumps([{'token':token_a,'owner_id':'account-a'},{'token':token_b,'owner_id':'account-b','quotas':{'request_bytes':64}}])
        with tempfile.TemporaryDirectory() as tmp,patch.object(core,'DB',Path(tmp)/'db'),patch.dict('os.environ',{'FIXLAB_AUTH_MODE':'required','FIXLAB_AUTH_TOKENS':config,'FIXLAB_RETENTION_DAYS':'30'}):
            sid=core.save({'id':'private','original_code':'x=1','analysis':{'summary':'Private','fixed_code':'x=1','tests':'pass'},'review':'pending'},'private','account-a')
            accepted=self.request('/api/analyze',{'code':'def f(): return 1','error':''},token=token_a)
            self.assertEqual(self.request('/api/sessions',token=token_b),[])
            self.expect_http(404,'/api/sessions/'+sid,token=token_b)
            self.expect_http(404,'/api/jobs/'+accepted['job_id'],token=token_b)
            self.expect_http(404,'/api/jobs/'+accepted['job_id']+'/cancel',{},token=token_b)
            for path,data in (
                ('/api/edit',{'id':sid,'fixed_code':'x=2','tests':'pass'}),
                ('/api/delete',{'id':sid}),
                ('/api/review',{'id':sid,'review':'accepted'}),
                ('/api/run',{'id':sid}),
            ):
                self.expect_http(404,path,data,token_b)
            self.expect_http(413,'/api/analyze',{'code':'x'*100,'error':''},token_b)
            self.assertEqual(self.request('/api/sessions/'+sid,token=token_a)['id'],'private')
    def test_review_edit_delete_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(core,'DB',Path(tmp)/'db'):
            sid=core.save({'id':'example','original_code':'x=1','analysis':{'summary':'Example'},'review':'pending'},'example')
            self.assertEqual(self.request('/api/review',{'id':sid,'review':'accepted'})['review'],'accepted')
            edited=self.request('/api/edit',{'id':sid,'fixed_code':'x=2','tests':'import unittest'})
            self.assertEqual(edited['review'],'pending')
            self.assertEqual(len(self.request('/api/sessions')),1)
            self.assertTrue(self.request('/api/delete',{'id':sid})['deleted'])
            self.assertEqual(self.request('/api/sessions'),[])
