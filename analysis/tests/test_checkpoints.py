"""Checks for the Windows replacement failure observed during the study."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_study import atomic_json, validate_chunk

class Checkpoints(unittest.TestCase):
    def test_atomic_replacement_retries_transient_windows_lock(self):
        import os
        real_replace = os.replace
        attempts = []
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'data.json'
            path.write_text('{"old":true}', encoding='utf-8')
            def replacement(source, destination):
                attempts.append(1)
                if len(attempts)<3:
                    self.assertEqual(json.loads(path.read_text()), {'old':True})
                    raise PermissionError('temporary sharing lock')
                real_replace(source, destination)
            with patch('run_study.os.replace', side_effect=replacement), patch('run_study.time.sleep'):
                atomic_json(path, {'new':True})
            self.assertEqual(len(attempts), 3)
            self.assertEqual(json.loads(path.read_text()), {'new':True})

    def test_corrupt_cached_counts_and_metadata_rejected(self):
        config = dict(games=1, limit=1, seed=7, start=0)
        valid = dict(games=1, outcomes=[0,0,0,0,0,1], duration=[0,1], turns=1,
                     actions=[1,0,0,0,0], passes=0, conservation_checks=2, seed=7, start=0, limit=1)
        validate_chunk(valid, config)
        for key, bad in [('outcomes',[0]*6), ('turns',2), ('conservation_checks',1), ('seed',8)]:
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                validate_chunk(dict(valid, **{key:bad}), config)

if __name__=='__main__': unittest.main()
