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


def run_core(processes, algorithm, **kwargs):
    simulator = SimulatorCore(max_processes=0, **kwargs)
    simulator.pending = sorted(
        copy.deepcopy(processes), key=lambda process: process.arrival_time
    )
    simulator._admit_arrivals()
    simulator._switch_algorithm(algorithm)
    steps = 0
    while not simulator.is_episode_done() and steps < 1000:
        simulator.tick()
        steps += 1
    if not simulator.is_episode_done():
        raise AssertionError("core simulator did not finish the test workload")
    return simulator.completed


class RoundRobinTests(unittest.TestCase):
    def test_quantum_expiration_and_arrival_during_execution(self):
        workload = [Process("A", 0, 5), Process("B", 1, 1)]
        result = simulate_round_robin(workload, quantum=2)
        completed = {process.pid: process for process in result["completed"]}

        self.assertEqual(completed["B"].start_time, 2)
        self.assertEqual(completed["B"].completion_time, 3)
        self.assertEqual(completed["A"].completion_time, 6)
        self.assertEqual(completed["A"].waiting_time, 1)
        self.assertEqual(completed["A"].response_time, 0)
        self.assertEqual(completed["A"].turnaround_time, 6)

    def test_idle_period_and_configured_quantum_in_core_match_standalone(self):
        workload = [Process("late", 4, 5)]
        standalone = simulate_round_robin(workload, quantum=2)["completed"]
        stepped = run_core(workload, ALGO_ROUND_ROBIN, quantum=2)

        for result in (standalone, stepped):
            process = result[0]
            self.assertEqual(process.start_time, 4)
            self.assertEqual(process.completion_time, 9)
            self.assertEqual(process.waiting_time, 0)
            self.assertEqual(process.turnaround_time, 5)


class PriorityTests(unittest.TestCase):
    def test_lowest_numeric_priority_runs_first_and_ties_are_stable(self):
        workload = [
            Process("first", 0, 2, priority=1),
            Process("high", 0, 1, priority=0),
            Process("tie", 0, 1, priority=1),
        ]
        result = simulate_priority_scheduling(workload)["completed"]
        by_pid = {process.pid: process for process in result}

        self.assertEqual(by_pid["high"].start_time, 0)
        self.assertEqual(by_pid["first"].start_time, 1)
        self.assertEqual(by_pid["tie"].start_time, 3)

    def test_non_preemptive_arrival_semantics_match_core(self):
        workload = [
            Process("running", 0, 4, priority=2),
            Process("arrives-later", 1, 1, priority=0),
        ]
        standalone = simulate_priority_scheduling(workload)["completed"]
        stepped = run_core(workload, ALGO_PRIORITY, quantum=2)

        for result in (standalone, stepped):
            by_pid = {process.pid: process for process in result}
            self.assertEqual(by_pid["running"].completion_time, 4)
            self.assertEqual(by_pid["arrives-later"].start_time, 4)
            self.assertEqual(by_pid["arrives-later"].waiting_time, 3)


class MLFQTests(unittest.TestCase):
    def test_new_high_level_job_runs_before_demoted_job(self):
        workload = [Process("long", 0, 9), Process("new", 2, 1)]
        standalone = simulate_mlfq(workload, quantums=(2, 3, 4))["completed"]
        stepped = run_core(
            workload, ALGO_MLFQ, mlfq_quantums=(2, 3, 4)
        )

        for result in (standalone, stepped):
            by_pid = {process.pid: process for process in result}
            self.assertEqual(by_pid["new"].start_time, 2)
            self.assertEqual(by_pid["new"].completion_time, 3)
            self.assertEqual(by_pid["long"].completion_time, 10)
            self.assertEqual(by_pid["long"].cpu_execution_time, 9)

    def test_periodic_boost_prevents_indefinite_demotion(self):
        workload = [
            Process("long", 0, 10),
            Process("short", 2, 1),
            Process("waiting", 3, 1),
        ]
        standalone = simulate_mlfq(
            workload, quantums=(2, 3), boost_interval=4
        )["completed"]
        stepped = run_core(
            workload,
            ALGO_MLFQ,
            mlfq_quantums=(2, 3),
            mlfq_boost_interval=4,
        )

        for result in (standalone, stepped):
            by_pid = {process.pid: process for process in result}
            self.assertEqual(by_pid["long"].completion_time, 12)
            self.assertEqual(by_pid["long"].state, Process.COMPLETED)
            for process in result:
                self.assertEqual(
                    process.turnaround_time,
                    process.waiting_time + process.cpu_execution_time,
                )

    def test_policy_switch_during_slice_keeps_process_schedulable(self):
        simulator = SimulatorCore(
            max_processes=0, quantum=2, mlfq_quantums=(2, 3)
        )
        simulator.pending = [Process("switching", 0, 5)]
        simulator._admit_arrivals()
        simulator.apply_action(3)
        simulator.tick()
        self.assertEqual(simulator.time, 2)

        simulator.apply_action(1)
        while not simulator.is_episode_done():
            simulator.tick()

        self.assertEqual(len(simulator.completed), 1)
        self.assertEqual(simulator.completed[0].completion_time, 5)

    def test_final_mlfq_completion_terminates_without_extra_idle_tick(self):
        simulator = SimulatorCore(max_processes=0, mlfq_quantums=(2, 3))
        simulator.pending = [Process("last", 0, 1)]
        simulator._admit_arrivals()
        simulator.apply_action(3)

        self.assertTrue(simulator.tick())
        self.assertTrue(simulator.is_episode_done())


if __name__ == "__main__":
    unittest.main()
