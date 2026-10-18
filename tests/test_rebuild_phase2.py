import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/rebuild_phase2.py'
spec = importlib.util.spec_from_file_location('rebuild_phase2', SCRIPT)
rebuild = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rebuild)


class RebuildPhase2Tests(unittest.TestCase):
    def test_existing_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / 'marker'
            marker.write_text('preserve')
            with self.assertRaises(FileExistsError):
                rebuild.rebuild(directory)
            self.assertEqual(marker.read_text(), 'preserve')

    def test_source_tree_is_rejected(self):
        with self.assertRaises(ValueError):
            rebuild.rebuild(rebuild.REPO / 'private_results/rebuild')

    def test_default_runs_only_procedural(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(rebuild.subprocess, 'run') as run:
            output = Path(directory) / 'new'
            rebuild.rebuild(output)
            self.assertEqual(run.call_count, 3)
            commands = [call.args[0] for call in run.call_args_list]
            self.assertTrue(all('evaluate_phase2_validation.py' not in ' '.join(c) for c in commands))
            self.assertIn('--zero-limit-only', commands[1])
            record = json.loads((output / 'rebuild.json').read_text())
            self.assertEqual(record['status'], 'complete')
            self.assertFalse(record['real_validation_requested'])
            self.assertEqual(run.call_args.kwargs['env']['OPENBLAS_NUM_THREADS'], '1')

    def test_failure_preserves_status(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(rebuild.subprocess, 'run', side_effect=RuntimeError('failed')):
            output = Path(directory) / 'new'
            with self.assertRaises(RuntimeError):
                rebuild.rebuild(output)
            self.assertEqual(json.loads((output / 'rebuild.json').read_text())['status'], 'failed; partial output preserved')
