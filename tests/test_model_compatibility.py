import json
import tempfile
import unittest
from pathlib import Path

from rl_agent.model_compatibility import validate_resume_metadata
from rl_agent.scheduler_env import LEARNING_SPEC_VERSION


class ModelCompatibilityTests(unittest.TestCase):
    def test_current_learning_spec_can_be_resumed(self):
        with tempfile.TemporaryDirectory() as directory:
            metadata_path = Path(directory) / "training_metadata.json"
            metadata_path.write_text(
                json.dumps({"learning_spec": {"version": LEARNING_SPEC_VERSION}}),
                encoding="utf-8",
            )
            self.assertEqual(
                validate_resume_metadata(Path(directory) / "trained_model.zip")["version"],
                LEARNING_SPEC_VERSION,
            )

    def test_old_or_missing_learning_spec_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            metadata_path = Path(directory) / "training_metadata.json"
            metadata_path.write_text(json.dumps({"algorithm": "DQN"}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "incompatible"):
                validate_resume_metadata(Path(directory) / "trained_model.zip")


if __name__ == "__main__":
    unittest.main()
