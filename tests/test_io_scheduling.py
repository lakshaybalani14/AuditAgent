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
from simulator_core import (  # noqa: E402
    ALGO_MLFQ,
    ALGO_PRIORITY,
    ALGO_ROUND_ROBIN,
    SimulatorCore,
)


def make_core(processes, algorithm, **kwargs):
    simulator = SimulatorCore(max_processes=0, **kwargs)
    simulator.pending = sorted(
        copy.deepcopy(processes), key=lambda process: process.arrival_time
    )
    simulator._admit_arrivals()
    simulator.apply_action({ALGO_ROUND_ROBIN: 1, ALGO_PRIORITY: 2, ALGO_MLFQ: 3}[algorithm])
    return simulator


def finish_core(simulator):
    steps = 0
    while not simulator.is_episode_done() and steps < 1000:
        simulator.tick()
        steps += 1
    if not simulator.is_episode_done():
        raise AssertionError("simulator did not finish the I/O workload")
    return simulator.completed


class CoreIOEventTests(unittest.TestCase):
    def test_blocks_at_cpu_offset_and_wakes_at_completion(self):
        process = Process("io", 0, 5, io_requests=[(2, 3)])
        other = Process("cpu", 0, 5)
        simulator = make_core([process, other], ALGO_ROUND_ROBIN, quantum=10)

        self.assertFalse(simulator.tick())
        blocked = next(item for item in simulator.blocked if item[2].pid == "io")
        self.assertEqual(simulator.time, 2)
        self.assertEqual(blocked[0], 5)
        self.assertEqual(blocked[2].state, Process.BLOCKED)
        self.assertEqual(blocked[2].remaining_time, 3)
        self.assertEqual(blocked[2].cpu_execution_time, 2)
        with self.assertRaises(ValueError):
            blocked[2].execute_cpu(1, simulator.time)

        # The CPU runs the other process while the first process is blocked.
        self.assertTrue(simulator.tick())
        io_process = next(item for item in simulator.ready_queue if item.pid == "io")
        self.assertEqual(io_process.state, Process.READY)
        self.assertEqual(io_process.last_ready_time, 5)
        self.assertEqual(io_process.cpu_execution_time, 2)
        self.assertIsNone(io_process.io_completion_time)

        self.assertTrue(simulator.tick())
        io_process = next(item for item in simulator.completed if item.pid == "io")
        self.assertEqual(io_process.completion_time, 10)
        self.assertEqual(io_process.waiting_time, 2)
        self.assertEqual(io_process.response_time, 0)
        self.assertEqual(io_process.turnaround_time, 10)
        self.assertEqual(io_process.io_time, 3)

    def test_simultaneous_wakeups_and_arrival_have_stable_order(self):
        workload = [
            Process("io-a", 0, 5, io_requests=[(1, 4)]),
            Process("io-b", 0, 2, io_requests=[(1, 3)]),
            Process("cpu", 0, 4),
            Process("arrives-at-wakeup", 5, 1),
        ]
        simulator = make_core(workload, ALGO_ROUND_ROBIN, quantum=10)

        simulator.tick()  # io-a blocks at t=1, wake at t=5
        simulator.tick()  # io-b blocks at t=2, wake at t=5
        self.assertEqual(len(simulator.blocked), 2)
        simulator.tick()  # CPU-bound process runs through t=6

        self.assertEqual(
            [process.pid for process in simulator.ready_queue],
            ["arrives-at-wakeup", "io-a", "io-b"],
        )
        self.assertEqual(simulator.ready_queue[1].last_ready_time, 5)
        self.assertEqual(simulator.ready_queue[2].last_ready_time, 5)
        completed = finish_core(simulator)
        by_pid = {process.pid: process for process in completed}
        for process in completed:
            self.assertEqual(
                process.turnaround_time,
                process.waiting_time + process.cpu_execution_time + process.io_time,
            )
        self.assertEqual(by_pid["io-a"].completion_time, 11)
        self.assertEqual(by_pid["io-b"].completion_time, 12)


class StandaloneIOAlgorithmTests(unittest.TestCase):
    def test_all_policies_match_core_with_io(self):
        workload = [
            Process("io", 0, 4, io_requests=[(2, 2)]),
            Process("cpu", 0, 3),
        ]
        cases = [
            (
                simulate_round_robin,
                {"quantum": 2},
                ALGO_ROUND_ROBIN,
                {"quantum": 2},
            ),
            (
                simulate_priority_scheduling,
                {},
                ALGO_PRIORITY,
                {"quantum": 2},
            ),
            (
                simulate_mlfq,
                {"quantums": (2, 3)},
                ALGO_MLFQ,
                {"mlfq_quantums": (2, 3)},
            ),
        ]

        for standalone_fn, standalone_kwargs, algo, core_kwargs in cases:
            with self.subTest(algorithm=standalone_fn.__name__):
                standalone = standalone_fn(workload, **standalone_kwargs)["completed"]
                core = finish_core(make_core(workload, algo, **core_kwargs))
                expected = {
                    process.pid: (
                        process.start_time,
                        process.completion_time,
                        process.waiting_time,
                        process.response_time,
                        process.turnaround_time,
                        process.cpu_execution_time,
                        process.io_time,
                    )
                    for process in standalone
                }
                actual = {
                    process.pid: (
                        process.start_time,
                        process.completion_time,
                        process.waiting_time,
                        process.response_time,
                        process.turnaround_time,
                        process.cpu_execution_time,
                        process.io_time,
                    )
                    for process in core
                }
                self.assertEqual(actual, expected)
                for process in standalone:
                    self.assertEqual(
                        process.turnaround_time,
                        process.waiting_time + process.cpu_execution_time + process.io_time,
                    )

    def test_multiple_io_requests_are_consumed_in_order(self):
        workload = [
            Process("multi-io", 0, 5, io_requests=[(1, 2), (3, 1)])
        ]
        cases = [
            (simulate_round_robin, {"quantum": 2}, ALGO_ROUND_ROBIN, {"quantum": 2}),
            (simulate_priority_scheduling, {}, ALGO_PRIORITY, {}),
            (
                simulate_mlfq,
                {"quantums": (2, 3)},
                ALGO_MLFQ,
                {"mlfq_quantums": (2, 3)},
            ),
        ]
        for standalone_fn, standalone_kwargs, algo, core_kwargs in cases:
            with self.subTest(algorithm=standalone_fn.__name__):
                standalone = standalone_fn(workload, **standalone_kwargs)["completed"][0]
                stepped = finish_core(make_core(workload, algo, **core_kwargs))[0]
                for process in (standalone, stepped):
                    self.assertEqual(process.io_time, 3)
                    self.assertEqual(process.next_io_request_index, 2)
                    self.assertEqual(process.completion_time, 8)
                    self.assertEqual(process.cpu_execution_time, 5)

    def test_standalone_policies_handle_simultaneous_io_wakeups(self):
        workload = [
            Process("io-a", 0, 5, io_requests=[(1, 4)]),
            Process("io-b", 0, 2, io_requests=[(1, 3)]),
            Process("cpu", 0, 4),
            Process("arrival", 5, 1),
        ]
        cases = [
            (simulate_round_robin, {"quantum": 10}, ALGO_ROUND_ROBIN, {"quantum": 10}),
            (simulate_priority_scheduling, {}, ALGO_PRIORITY, {"quantum": 10}),
            (
                simulate_mlfq,
                {"quantums": (2, 3)},
                ALGO_MLFQ,
                {"mlfq_quantums": (2, 3)},
            ),
        ]
        for standalone_fn, standalone_kwargs, algo, core_kwargs in cases:
            with self.subTest(algorithm=standalone_fn.__name__):
                standalone = standalone_fn(workload, **standalone_kwargs)["completed"]
                core = finish_core(make_core(workload, algo, **core_kwargs))
                fields = lambda processes: {
                    process.pid: (
                        process.start_time,
                        process.completion_time,
                        process.waiting_time,
                        process.response_time,
                        process.turnaround_time,
                        process.cpu_execution_time,
                        process.io_time,
                    )
                    for process in processes
                }
                self.assertEqual(fields(core), fields(standalone))


if __name__ == "__main__":
    unittest.main()
