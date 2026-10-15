import json
import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import rl_agent.generate_decision_log as decision_generator
from rl_agent.generate_decision_log import snapshot_processes, write_decision_log
from rl_agent.scheduler_env import SchedulerEnv
from explainability.explainer import build_prompt, explanation_error_message


class DecisionLogWriterTests(unittest.TestCase):
    def test_writes_to_the_requested_path_without_touching_other_logs(self):
        with tempfile.TemporaryDirectory() as directory:
            existing = Path(directory) / "decision_log.json"
            existing.write_text('[{"sample": true}]', encoding="utf-8")
            output = Path(directory) / "generated" / "decision_log.json"
            decisions = [{"action": 2, "state": {"time": 4}}]

            write_decision_log(decisions, output)

            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), decisions)
            self.assertEqual(existing.read_text(encoding="utf-8"), '[{"sample": true}]')
            self.assertEqual(list(output.parent.iterdir()), [output])


class ProcessSnapshotTests(unittest.TestCase):
    def test_snapshot_records_real_process_state_and_is_json_serializable(self):
        env = SchedulerEnv(
            max_processes=3,
            scenario="short_jobs",
            workload_config={
                "arrival_range": (0, 0),
                "burst_range": (4, 4),
                "priority_range": (0, 2),
                "io_probability": 0,
            },
        )
        try:
            env.sim.reset(seed=42)
            before = snapshot_processes(env.sim)
            self.assertEqual(len(before), 3)
            self.assertEqual({process["state"] for process in before}, {"READY"})
            self.assertTrue(all(process["remaining_time"] == process["burst_time"] for process in before))
            json.dumps(before)

            env.sim.apply_action(3)
            after = snapshot_processes(env.sim)
            self.assertEqual(len(after), 3)
            self.assertTrue(any(process["queue_level"] is not None for process in after))
            json.dumps(after)
        finally:
            env.close()


class GeminiPromptTests(unittest.TestCase):
    def test_prompt_uses_the_policy_input_and_real_q_values(self):
        prompt = build_prompt(
            {
                "time": 5,
                "queue_length": 2,
                "avg_wait_time": 1.5,
                "max_wait_time": 3,
                "num_io_bound": 1,
                "num_cpu_bound": 1,
                "current_algo": 0,
                "is_starving": False,
            },
            1,
            observation={"ready_fraction": 0.5},
            q_values={"switch to Round Robin": 1.25, "no change": 0.75},
        )

        self.assertIn("Exact normalized feature values", prompt)
        self.assertIn("ready_fraction=0.500", prompt)
        self.assertIn("switch to Round Robin=1.250", prompt)
        self.assertIn("higher is preferred", prompt)


class ExplanationQuotaTests(unittest.TestCase):
    class QuotaError(Exception):
        code = 429

    def test_quota_message_keeps_provider_details_out_of_the_log(self):
        message = explanation_error_message(self.QuotaError("private-key-and-request"))
        self.assertIn("HTTP 429", message)
        self.assertIn("quota", message)
        self.assertNotIn("private-key-and-request", message)

    def test_stream_saves_all_decisions_and_stops_requests_after_quota_error(self):
        records = [
            {"episode": 1, "step": step, "state": {"time": step}, "action": 0,
             "observation": {}, "q_values": {}}
            for step in range(1, 4)
        ]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run.json"
            with patch.dict(os.environ, {"EXPLANATION_PROVIDER": "gemini"}), \
                 patch.object(decision_generator, "iter_real_decisions", return_value=iter(records)), \
                 patch.object(decision_generator, "create_client", return_value=object()), \
                 patch.object(decision_generator, "explain_decision", side_effect=self.QuotaError()) as request, \
                 contextlib.redirect_stdout(io.StringIO()) as stdout, \
                 contextlib.redirect_stderr(io.StringIO()):
                decision_generator.main(n=3, output_path=output, stream_jsonl=True)

            self.assertEqual(request.call_count, 1)
            saved = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(len(saved), 3)
            self.assertTrue(all(entry["explanation_status"] == "unavailable" for entry in saved))
            self.assertTrue(all("HTTP 429" in entry["explanation_error"] for entry in saved))
            events = [json.loads(line)["type"] for line in stdout.getvalue().splitlines()]
            self.assertEqual(events[:4], ["decision", "decision", "decision", "decisions_complete"])
            self.assertEqual(events[-1], "complete")


if __name__ == "__main__":
    unittest.main()
