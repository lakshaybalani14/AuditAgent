import unittest

from rl_agent.evaluate import run_episode, summarize_runs
from rl_agent.scheduler_env import SchedulerEnv


class EvaluationMetricsTests(unittest.TestCase):
    def test_partial_episode_cpu_utilization_includes_unfinished_processes(self):
        env = SchedulerEnv(max_processes=3, workload_profiles=("short_job_heavy",))
        try:
            result = run_episode(
                env,
                "Round Robin",
                lambda observation, step: 1 if step == 0 else 0,
                "short_job_heavy",
                seed=10,
                max_steps=2,
            )
            processes = (
                env.sim.completed
                + env.sim.pending
                + env.sim.ready_queue
                + [event[2] for event in env.sim.blocked]
            )
            if env.sim.running_process is not None:
                processes.append(env.sim.running_process)
            expected = sum(process.cpu_execution_time for process in processes) / env.sim.time
        finally:
            env.close()

        self.assertFalse(result["episode_terminated"])
        self.assertGreater(expected, 0.0)
        self.assertAlmostEqual(result["cpu_utilization"], expected)

    def test_episode_reports_process_outcomes_and_action_counts(self):
        env = SchedulerEnv(max_processes=5, workload_profiles=("io_heavy",))
        try:
            result = run_episode(
                env,
                "Round Robin",
                lambda observation, step: 1 if step == 0 else 0,
                "io_heavy",
                seed=918,
                max_steps=500,
            )
        finally:
            env.close()

        self.assertTrue(result["episode_terminated"])
        self.assertEqual(result["processes_completed"], 5)
        self.assertEqual(result["process_completion_rate"], 1.0)
        self.assertEqual(result["action_counts"]["round_robin"], 1)
        self.assertEqual(
            sum(result["action_counts"].values()), result["episode_steps"]
        )
        for key in (
            "mean_process_waiting_time_ticks",
            "p95_process_waiting_time_ticks",
            "mean_process_turnaround_time_ticks",
            "mean_process_response_time_ticks",
            "throughput_processes_per_tick",
            "cpu_utilization",
        ):
            self.assertGreaterEqual(result[key], 0.0)
        self.assertLessEqual(result["cpu_utilization"], 1.0)

    def test_summary_aggregates_action_counts_and_outcomes(self):
        env = SchedulerEnv(max_processes=3, workload_profiles=("short_job_heavy",))
        try:
            result = run_episode(
                env,
                "Round Robin",
                lambda observation, step: 1 if step == 0 else 0,
                "short_job_heavy",
                seed=143,
                max_steps=500,
            )
        finally:
            env.close()

        summary = summarize_runs([result])
        self.assertEqual(summary["action_counts"], result["action_counts"])
        self.assertAlmostEqual(sum(summary["action_fractions"].values()), 1.0)
        self.assertEqual(
            summary["mean_process_waiting_time_ticks"],
            result["mean_process_waiting_time_ticks"],
        )


if __name__ == "__main__":
    unittest.main()

