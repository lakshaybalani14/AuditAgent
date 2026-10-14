import random
import sys
import unittest
from pathlib import Path

SIMULATOR_DIR = Path(__file__).resolve().parents[1] / "simulator"
sys.path.insert(0, str(SIMULATOR_DIR))

from process import Process  # noqa: E402
from simulator_core import SimulatorCore  # noqa: E402
from workload_profiles import (  # noqa: E402
    PROFILE_NAMES,
    generate_process_specs,
    normalize_workload_profiles,
)


def workload_definition(processes):
    return [
        (
            process.pid,
            process.arrival_time,
            process.burst_time,
            process.priority,
            process.is_io_bound,
            tuple(
                (request.after_cpu_time, request.duration)
                for request in process.io_requests
            ),
        )
        for process in sorted(processes, key=lambda process: process.pid)
    ]


class WorkloadProfileTests(unittest.TestCase):
    def test_normalization_accepts_all_and_rejects_unknown_profiles(self):
        self.assertEqual(normalize_workload_profiles("all"), PROFILE_NAMES)
        self.assertEqual(
            normalize_workload_profiles("cpu_heavy, io_heavy"),
            ("cpu_heavy", "io_heavy"),
        )
        with self.assertRaises(ValueError):
            normalize_workload_profiles("not_a_profile")

    def test_generator_is_seeded_and_emits_real_io_requests(self):
        first = generate_process_specs("io_heavy", 30, random.Random(31))
        second = generate_process_specs("io_heavy", 30, random.Random(31))
        self.assertEqual(first, second)
        self.assertTrue(
            any(spec["io_requests"] for spec in first if spec["burst_time"] > 1)
        )
        for spec in first:
            process = Process(**spec)
            for request in process.io_requests:
                self.assertGreater(request.after_cpu_time, 0)
                self.assertLess(request.after_cpu_time, process.burst_time)
                self.assertGreater(request.duration, 0)

    def test_core_reset_routes_profile_and_seed_to_the_generator(self):
        simulator = SimulatorCore(max_processes=20)
        simulator.reset(seed=72, options={"workload_profile": "io_heavy"})
        first = workload_definition(simulator.pending + simulator.ready_queue)
        self.assertEqual(simulator.current_workload_profile, "io_heavy")

        simulator.reset(seed=72, options={"workload_profile": "io_heavy"})
        self.assertEqual(
            first,
            workload_definition(simulator.pending + simulator.ready_queue),
        )

    def test_core_keeps_constructor_scenario_when_profile_is_not_requested(self):
        simulator = SimulatorCore(
            max_processes=5,
            seed=12,
            scenario="short_jobs",
            workload_config={"arrival_range": (0, 0), "burst_range": (1, 2)},
        )
        simulator.reset(seed=12)
        self.assertIsNone(simulator.current_workload_profile)
        self.assertTrue(
            all(process.arrival_time == 0 for process in simulator.ready_queue)
        )


if __name__ == "__main__":
    unittest.main()

