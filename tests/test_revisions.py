import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
import core

class RevisionTests(unittest.TestCase):
    def test_edit_invalidates_evidence_and_review(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(core,'DB',Path(tmp)/'db'):
            sid=core.save({'original_code':'x=1','analysis':{'summary':'Example'},'results':{'fixed':{'passed':True}},'review':'accepted'})
            session=core.edit(sid,'x=2','import unittest')
            self.assertIsNone(session['results'])
            self.assertEqual(session['review'],'pending')
            self.assertEqual(session['revision'],2)
            self.assertIn('+x=2',session['diff'])
            core.delete(sid)
            with self.assertRaises(ValueError):core.get(sid)
    def test_invalid_edit_preserves_session(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(core,'DB',Path(tmp)/'db'):
            sid=core.save({'analysis':{'summary':'Example'}})
            with self.assertRaises(SyntaxError):core.edit(sid,'def :','pass')
            self.assertEqual(core.get(sid),{'analysis':{'summary':'Example'}})

class GeneratedTestImports(unittest.TestCase):
    def test_missing_solution_import_repaired_after_future_import(self):
        value={'summary':'Bug','explanation':'Fix','fixed_code':'def average(xs): return 0','tests':'"""Tests."""\nfrom __future__ import annotations\nimport unittest\nclass T(unittest.TestCase):\n    def test_empty(self): self.assertEqual(average([]),0)\n'}
        result=core.validate_analysis(value)
        self.assertIn('from solution import average',result['tests'])
        compile(result['tests'],'tests.py','exec')
