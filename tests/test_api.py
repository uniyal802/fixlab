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
    def request(self,path,data=None,origin=None):
        headers={'Content-Type':'application/json'}
        if origin: headers['Origin']=origin
        req=urllib.request.Request(self.base+path,data=json.dumps(data).encode() if data is not None else None,headers=headers)
        with urllib.request.urlopen(req) as response:return json.load(response)
    def test_cross_origin_write_rejected(self):
        with self.assertRaises(urllib.error.HTTPError) as context:self.request('/api/analyze',{'code':'pass'},'https://example.com')
        self.assertEqual(context.exception.code,403)
    def test_review_edit_delete_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(core,'DB',Path(tmp)/'db'):
            sid=core.save({'id':'example','original_code':'x=1','analysis':{'summary':'Example'},'review':'pending'},'example')
            self.assertEqual(self.request('/api/review',{'id':sid,'review':'accepted'})['review'],'accepted')
            edited=self.request('/api/edit',{'id':sid,'fixed_code':'x=2','tests':'import unittest'})
            self.assertEqual(edited['review'],'pending')
            self.assertEqual(len(self.request('/api/sessions')),1)
            self.assertTrue(self.request('/api/delete',{'id':sid})['deleted'])
            self.assertEqual(self.request('/api/sessions'),[])
