import math
import unittest

import numpy as np

from rl_agent.scheduler_env import SchedulerEnv


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
        self.assertEqual(observation.shape, (7,))
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
