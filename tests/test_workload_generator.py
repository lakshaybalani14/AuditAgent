import copy
import sys
import unittest
from pathlib import Path

SIMULATOR_DIR = Path(__file__).resolve().parents[1] / "simulator"
sys.path.insert(0, str(SIMULATOR_DIR))

from process import Process  # noqa: E402
from scheduler_algorithms import (  # noqa: E402
    simulate_mlfq,
    simulate_priority_scheduling,
    simulate_round_robin,
)
from simulator_core import SimulatorCore  # noqa: E402
from workload_generator import SCENARIOS, generate_workload  # noqa: E402


def definition(processes):
    return [
        (
            process.pid,
            process.arrival_time,
            process.burst_time,
            process.priority,
            tuple((request.after_cpu_time, request.duration) for request in process.io_requests),
        )
        for process in processes
    ]


class WorkloadGeneratorTests(unittest.TestCase):
    def test_same_seed_and_configuration_reproduce_definitions(self):
        config = dict(
            seed=421,
            count=15,
            scenario="mixed_cpu_io",
            arrival_range=(0, 12),
            burst_range=(2, 12),
            priority_range=(0, 4),
            io_probability=0.8,
        )
        self.assertEqual(
            definition(generate_workload(**config)),
            definition(generate_workload(**config)),
        )

    def test_different_seeds_produce_different_workloads(self):
        first = generate_workload(1, count=20, scenario="mixed_cpu_io")
        second = generate_workload(2, count=20, scenario="mixed_cpu_io")
        self.assertNotEqual(definition(first), definition(second))

    def test_profiles_and_configurations_make_valid_processes(self):
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario):
                processes = generate_workload(
                    87,
                    count=12,
                    scenario=scenario,
                    arrival_range=(0, 9),
                    burst_range=(1, 10),
                    priority_range=(0, 3),
                    io_probability=1,
                    io_request_count_range=(1, 2),
                )
                self.assertEqual(len(processes), 12)
                self.assertTrue(all(isinstance(process, Process) for process in processes))
                for process in processes:
                    self.assertGreaterEqual(process.arrival_time, 0)
                    self.assertGreaterEqual(process.burst_time, 1)
                    self.assertGreaterEqual(process.priority, 0)
                    self.assertEqual(process.remaining_time, process.burst_time)
                    previous = 0
                    for request in process.io_requests:
                        self.assertGreater(request.after_cpu_time, previous)
                        self.assertLess(request.after_cpu_time, process.burst_time)
                        self.assertGreaterEqual(request.duration, 1)
                        previous = request.after_cpu_time

    def test_invalid_configuration_is_rejected(self):
        for kwargs in (
            {"seed": "4"},
            {"seed": 4, "count": -1},
            {"seed": 4, "scenario": "unknown"},
            {"seed": 4, "burst_range": (0, 3)},
            {"seed": 4, "io_probability": 1.1},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises((TypeError, ValueError)):
                generate_workload(**kwargs)

    def test_workload_is_reusable_across_algorithms_without_input_mutation(self):
        workload = generate_workload(
            203,
            count=8,
            scenario="mixed_cpu_io",
            arrival_range=(0, 4),
            burst_range=(3, 8),
            io_probability=0.75,
        )
        before = copy.deepcopy(workload)
        original_definition = definition(workload)

        for scheduler in (
            lambda items: simulate_round_robin(items, quantum=2),
            simulate_priority_scheduling,
            simulate_mlfq,
        ):
            result = scheduler(workload)
            self.assertEqual(len(result["completed"]), len(workload))
            self.assertTrue(all(item.state == Process.COMPLETED for item in result["completed"]))
            self.assertEqual(definition(workload), original_definition)
            self.assertEqual(
                [(p.state, p.remaining_time, p.cpu_execution_time) for p in workload],
                [(p.state, p.remaining_time, p.cpu_execution_time) for p in before],
            )

    def test_core_seed_restarts_the_same_workload_stream(self):
        simulator = SimulatorCore(max_processes=8, seed=77, scenario="short_jobs")
        first = definition(simulator.pending)
        simulator.reset(seed=77)
        self.assertEqual(first, definition(simulator.pending))


if __name__ == "__main__":
    unittest.main()
