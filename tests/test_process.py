import unittest

from simulator.process import IORequest, Process, ProcessState


class ProcessInitializationTests(unittest.TestCase):
    def test_initializes_legacy_and_runtime_fields(self):
        process = Process("job-1", 3, 8, priority=2, is_io_bound=True)

        self.assertEqual(process.pid, "job-1")
        self.assertEqual(process.arrival_time, 3)
        self.assertEqual(process.burst_time, 8)
        self.assertEqual(process.remaining_time, 8)
        self.assertEqual(process.priority, 2)
        self.assertEqual(process.state, ProcessState.NEW)
        self.assertIsNone(process.start_time)
        self.assertIsNone(process.completion_time)
        self.assertEqual(process.waiting_time, 0)
        self.assertEqual(process.cpu_execution_time, 0)
        self.assertEqual(process.last_ready_time, 3)

    def test_normalizes_configured_io_requests(self):
        process = Process(
            1, 0, 10, io_requests=[(3, 2), {"after_cpu_time": 7, "duration": 1}]
        )

        self.assertEqual(
            process.io_requests,
            [IORequest(after_cpu_time=3, duration=2), IORequest(after_cpu_time=7, duration=1)],
        )
        self.assertTrue(process.is_io_bound)


class ProcessLifecycleTests(unittest.TestCase):
    def test_valid_state_transitions_and_wait_accounting(self):
        process = Process("p", 0, 5)
        process.mark_ready(0)
        process.add_waiting_time(2)
        process.start(2)
        process.execute_cpu(2, 2)
        process.transition_to(ProcessState.READY)
        process.last_ready_time = 4
        process.add_waiting_time(3)
        process.start(7)
        process.execute_cpu(3, 7)

        self.assertEqual(process.state, ProcessState.COMPLETED)
        self.assertEqual(process.start_time, 2)
        self.assertEqual(process.completion_time, 10)
        self.assertEqual(process.remaining_time, 0)
        self.assertEqual(process.cpu_execution_time, 5)
        self.assertEqual(process.waiting_time, 5)
        self.assertTrue(process.is_finished())

    def test_rejects_illegal_transitions(self):
        process = Process("p", 0, 1)
        with self.assertRaises(ValueError):
            process.transition_to(ProcessState.RUNNING)
        process.mark_ready(0)
        with self.assertRaises(ValueError):
            process.block()

    def test_block_and_wakeup_transitions(self):
        process = Process("p", 0, 2)
        process.mark_ready(0)
        process.start(0)
        process.block()
        process.mark_ready(4)
        self.assertEqual(process.state, ProcessState.READY)
        self.assertEqual(process.last_ready_time, 4)


class ProcessValidationTests(unittest.TestCase):
    def test_rejects_invalid_core_fields(self):
        invalid_cases = [
            ("", 0, 1, 0),
            ("p", -1, 1, 0),
            ("p", 0, 0, 0),
            ("p", 0, 1, -1),
            ("p", True, 1, 0),
            ("p", 0, 1, 0.5),
        ]
        for pid, arrival, burst, priority in invalid_cases:
            with self.subTest(pid=pid, arrival=arrival, burst=burst, priority=priority):
                with self.assertRaises((TypeError, ValueError)):
                    Process(pid, arrival, burst, priority)

    def test_rejects_invalid_io_requests(self):
        invalid_requests = [
            [(0, 1)],
            [(3, 0)],
            [(4, 1), (3, 1)],
            [(5, 1)],
            [{"after_cpu_time": 2}],
        ]
        for requests in invalid_requests:
            with self.subTest(requests=requests):
                with self.assertRaises((TypeError, ValueError)):
                    Process("p", 0, 5, io_requests=requests)

    def test_rejects_execution_beyond_remaining_cpu(self):
        process = Process("p", 0, 2)
        process.mark_ready(0)
        process.start(0)
        with self.assertRaises(ValueError):
            process.execute_cpu(3, 0)

    def test_completion_is_idempotent_at_the_recorded_time(self):
        process = Process("p", 0, 1)
        process.mark_ready(0)
        process.start(0)
        process.execute_cpu(1, 0)

        process.complete(1)
        self.assertEqual(process.state, Process.COMPLETED)
        self.assertEqual(process.completion_time, 1)
        self.assertEqual(process.turnaround_time, 1)
        with self.assertRaises(ValueError):
            process.complete(2)


if __name__ == "__main__":
    unittest.main()
