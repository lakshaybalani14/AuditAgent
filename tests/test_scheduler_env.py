import math
import unittest

import numpy as np

from rl_agent.scheduler_env import OBSERVATION_FEATURES, SchedulerEnv


def make_env():
    return SchedulerEnv(
        max_processes=4,
        scenario="short_jobs",
        workload_config={
            "arrival_range": (0, 0),
            "burst_range": (1, 3),
            "priority_range": (0, 2),
            "io_probability": 0,
        },
    )


def workload_definition(env):
    processes = env.sim.pending + env.sim.ready_queue
    return sorted(
        (
            process.pid,
            process.arrival_time,
            process.burst_time,
            process.priority,
            tuple((request.after_cpu_time, request.duration) for request in process.io_requests),
        )
        for process in processes
    )


class SchedulerEnvironmentTests(unittest.TestCase):
    def assert_valid_observation(self, env, observation):
        self.assertEqual(observation.shape, (len(OBSERVATION_FEATURES),))
        self.assertTrue(np.all(observation >= 0.0))
        self.assertTrue(np.all(observation <= 1.0))
        self.assertEqual(observation.dtype, np.float32)
        self.assertTrue(env.observation_space.contains(observation))

    def test_seeded_reset_reproduces_the_same_workload(self):
        env = make_env()
        try:
            first_observation, _ = env.reset(seed=491)
            first_workload = workload_definition(env)
            second_observation, _ = env.reset(seed=491)

            self.assertEqual(first_workload, workload_definition(env))
            np.testing.assert_array_equal(first_observation, second_observation)
            self.assert_valid_observation(env, second_observation)
        finally:
            env.close()

    def test_selected_profile_reaches_simulator_and_is_reported(self):
        env = SchedulerEnv(max_processes=20, workload_profiles=("io_heavy",))
        try:
            _, info = env.reset(
                seed=741,
                options={"workload_profile": "io_heavy"},
            )
            self.assertEqual(info["workload_profile"], "io_heavy")
            self.assertEqual(env.sim.current_workload_profile, "io_heavy")
            processes = env.sim.pending + env.sim.ready_queue
            self.assertTrue(any(process.io_requests for process in processes))
            self.assertTrue(
                all(
                    process.io_requests
                    for process in processes
                    if process.is_io_bound and process.burst_time > 1
                )
            )
        finally:
            env.close()

    def test_profile_sampling_is_reproducible_from_environment_seed(self):
        env = SchedulerEnv(max_processes=10, workload_profiles="all")
        try:
            _, first_info = env.reset(seed=884)
            _, second_info = env.reset(seed=884)
            self.assertEqual(
                first_info["workload_profile"],
                second_info["workload_profile"],
            )
            self.assertEqual(
                first_info["workload_profile"],
                env.sim.current_workload_profile,
            )
        finally:
            env.close()

    def test_all_action_space_actions_execute_and_observations_stay_valid(self):
        env = make_env()
        try:
            self.assertEqual(env.action_space.n, 5)
            for action in range(env.action_space.n):
                observation, _ = env.reset(seed=100 + action)
                self.assert_valid_observation(env, observation)

                observation, reward, terminated, truncated, _ = env.step(action)
                self.assert_valid_observation(env, observation)
                self.assertTrue(math.isfinite(reward))
                self.assertIsInstance(terminated, bool)
                self.assertIsInstance(truncated, bool)
        finally:
            env.close()

    def test_reward_tracks_completed_process_waiting_time(self):
        env = make_env()
        try:
            observation, _ = env.reset(seed=916)
            total_reward = 0.0
            terminated = truncated = False
            steps = 0
            while not (terminated or truncated):
                observation, reward, terminated, truncated, info = env.step(0)
                total_reward += reward
                self.assertGreaterEqual(info["waiting_delta"], 0)
                steps += 1
                self.assertLess(steps, 100)
            completed_wait = sum(process.waiting_time for process in env.sim.completed)
            self.assertEqual(env.sim.get_total_waiting_time(), completed_wait)
            self.assertAlmostEqual(total_reward, -completed_wait)
        finally:
            env.close()

    def test_switch_penalty_is_charged_only_when_algorithm_changes(self):
        env = SchedulerEnv(
            max_processes=4,
            workload_profiles=("short_job_heavy",),
            switch_penalty=0.75,
        )
        try:
            env.reset(seed=29)
            _, reward, _, _, info = env.step(3)  # Switch from RR to MLFQ.
            self.assertTrue(info["scheduler_changed"])
            self.assertFalse(info["is_starving"])
            self.assertAlmostEqual(reward, -info["waiting_delta"] - 0.75)
        finally:
            env.close()

    def test_episode_terminates_with_every_process_completed(self):
        env = make_env()
        try:
            observation, _ = env.reset(seed=902)
            self.assert_valid_observation(env, observation)
            terminated = truncated = False
            steps = 0

            while not (terminated or truncated):
                action = steps % env.action_space.n
                observation, reward, terminated, truncated, _ = env.step(action)
                self.assert_valid_observation(env, observation)
                self.assertTrue(math.isfinite(reward))
                self.assertGreaterEqual(env.sim.time, 0)
                steps += 1
                self.assertLess(steps, 100)

            self.assertTrue(terminated)
            self.assertFalse(truncated)
            self.assertEqual(len(env.sim.completed), 4)
            self.assertTrue(
                all(process.state == "COMPLETED" for process in env.sim.completed)
            )
        finally:
            env.close()


if __name__ == "__main__":
    unittest.main()

