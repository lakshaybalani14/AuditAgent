"""Steppable scheduler used by the Gymnasium environment.

Priority is non-preemptive: after dispatch, the selected process keeps the CPU
across calls to ``tick`` until completion, even if a later action changes the
policy. Round Robin and MLFQ release a process at each quantum boundary.
"""

import heapq
import random

from process import Process
from scheduler_algorithms import (
    DEFAULT_MLFQ_BOOST_INTERVAL,
    DEFAULT_MLFQ_QUANTUMS,
)
from workload_generator import generate_workload
from workload_profiles import generate_process_specs, normalize_workload_profiles

ALGO_ROUND_ROBIN = 0
ALGO_PRIORITY = 1
ALGO_MLFQ = 2

STARVATION_THRESHOLD = DEFAULT_MLFQ_BOOST_INTERVAL


class SimulatorCore:
    def __init__(
        self,
        max_processes=10,
        quantum=2,
        mlfq_quantums=DEFAULT_MLFQ_QUANTUMS,
        mlfq_boost_interval=DEFAULT_MLFQ_BOOST_INTERVAL,
        seed=None,
        scenario="mixed_cpu_io",
        workload_config=None,
    ):
        self.max_processes = max_processes
        self.quantum = quantum
        self.mlfq_quantums = tuple(mlfq_quantums)
        self.mlfq_boost_interval = mlfq_boost_interval
        self.seed = seed
        self.scenario = scenario
        self.workload_config = dict(workload_config or {})
        self._rng = random.Random(seed)
        self.current_workload_profile = None
        if not self.mlfq_quantums or any(
            not isinstance(value, int) or isinstance(value, bool) or value <= 0
            for value in self.mlfq_quantums
        ):
            raise ValueError("mlfq_quantums must contain positive integers")
        if (
            not isinstance(self.mlfq_boost_interval, int)
            or isinstance(self.mlfq_boost_interval, bool)
            or self.mlfq_boost_interval <= 0
        ):
            raise ValueError("mlfq_boost_interval must be a positive integer")
        if not isinstance(self.quantum, int) or isinstance(self.quantum, bool) or self.quantum <= 0:
            raise ValueError("quantum must be a positive integer")
        self.time = 0
        self.current_algo = ALGO_ROUND_ROBIN
        self.ready_queue = []
        self.pending = []
        self.completed = []
        self.blocked = []
        self._io_event_sequence = 0
        self.mlfq_queues = [[] for _ in self.mlfq_quantums]
        self.running_process = None
        self.running_algorithm = None
        self.running_level = None
        self.processes = []
        self.reset()

    def reset(self, seed=None, options=None):
        if seed is not None:
            self.seed = seed
            self._rng.seed(seed)
        if options is not None and not isinstance(options, dict):
            raise TypeError("options must be a dictionary or None")
        options = options or {}
        requested_profile = options.get("workload_profile")
        if requested_profile is None:
            self.current_workload_profile = None
            workload = self._generate_process_batch()
        else:
            self.current_workload_profile = normalize_workload_profiles(
                requested_profile
            )[0]
            specs = generate_process_specs(
                self.current_workload_profile,
                self.max_processes,
                self._rng,
            )
            workload = [Process(**spec) for spec in specs]
        self.processes = list(workload)
        self.time = 0
        self.current_algo = ALGO_ROUND_ROBIN
        self.ready_queue = []
        self.pending = sorted(workload, key=lambda process: process.arrival_time)
        self.completed = []
        self.blocked = []
        self._io_event_sequence = 0
        self.mlfq_queues = [[] for _ in self.mlfq_quantums]
        self.running_process = None
        self.running_algorithm = None
        self.running_level = None
        self._admit_arrivals()

    def _generate_process_batch(self):
        episode_seed = self._rng.getrandbits(64)
        return generate_workload(
            seed=episode_seed,
            count=self.max_processes,
            scenario=self.scenario,
            **self.workload_config,
        )

    def _sync_ready_queue(self):
        if self.current_algo == ALGO_MLFQ:
            self.ready_queue = [
                process for queue in self.mlfq_queues for process in queue
            ]

    def _admit_arrivals(self):
        while self.pending and self.pending[0].arrival_time <= self.time:
            process = self.pending.pop(0)
            process.mark_ready(process.arrival_time)
            self._queue_ready(process)
        self._sync_ready_queue()

    def _queue_ready(self, process, level=0):
        if self.current_algo == ALGO_MLFQ:
            self.mlfq_queues[min(level, len(self.mlfq_queues) - 1)].append(process)
        else:
            self.ready_queue.append(process)

    def _process_events_through(self, limit):
        """Admit arrivals before simultaneous I/O wakeups, in stable order."""
        while True:
            next_arrival = self.pending[0].arrival_time if self.pending else None
            next_wakeup = self.blocked[0][0] if self.blocked else None
            candidates = [
                event_time for event_time in (next_arrival, next_wakeup)
                if event_time is not None and event_time <= limit
            ]
            if not candidates:
                break
            event_time = min(candidates)
            while self.pending and self.pending[0].arrival_time <= event_time:
                process = self.pending.pop(0)
                process.mark_ready(process.arrival_time)
                self._queue_ready(process)
            due = []
            while self.blocked and self.blocked[0][0] <= event_time:
                due.append(heapq.heappop(self.blocked))
            for wake_time, sequence, process, level in due:
                process.complete_io(wake_time)
                self._queue_ready(process, level if level is not None else 0)
        self._sync_ready_queue()

    def _switch_algorithm(self, new_algorithm):
        if new_algorithm == self.current_algo:
            return
        if self.current_algo == ALGO_MLFQ:
            self.ready_queue = [
                process for queue in self.mlfq_queues for process in queue
            ]
        if new_algorithm == ALGO_MLFQ:
            self.mlfq_queues = [[] for _ in self.mlfq_quantums]
            self.mlfq_queues[0].extend(self.ready_queue)
            self.ready_queue = []
        self.current_algo = new_algorithm
        self._sync_ready_queue()

    def get_state_summary(self):
        queue_length = len(self.ready_queue)
        if queue_length:
            ages = [self.time - process.last_ready_time for process in self.ready_queue]
            avg_wait_time = sum(ages) / queue_length
            max_wait_time = max(ages)
        else:
            avg_wait_time = 0.0
            max_wait_time = 0.0
        num_io_bound = sum(process.is_io_bound for process in self.ready_queue)
        return {
            "time": self.time,
            "queue_length": queue_length,
            "avg_wait_time": avg_wait_time,
            "max_wait_time": max_wait_time,
            "num_io_bound": num_io_bound,
            "num_cpu_bound": queue_length - num_io_bound,
            "current_algo": self.current_algo,
            "is_starving": max_wait_time > STARVATION_THRESHOLD,
        }

    def get_total_waiting_time(self):
        """Return all completed plus currently accrued READY waiting ticks.

        This is the exact objective measured by completed-process waiting time
        when the episode finishes, while still giving the learner dense credit
        during an episode.
        """
        total = 0
        for process in self.processes:
            total += process.waiting_time
            if process.state == Process.READY:
                total += self.time - process.last_ready_time
        return total

    def apply_action(self, action):
        if action == 0:
            return
        if action == 1:
            self._switch_algorithm(ALGO_ROUND_ROBIN)
        elif action == 2:
            self._switch_algorithm(ALGO_PRIORITY)
        elif action == 3:
            self._switch_algorithm(ALGO_MLFQ)
        elif action == 4:
            if self.ready_queue:
                oldest = max(
                    self.ready_queue,
                    key=lambda process: self.time - process.last_ready_time,
                )
                oldest.priority = max(0, oldest.priority - 1)
        else:
            raise ValueError(f"Unknown action: {action}")

    def _select_process(self):
        if self.current_algo == ALGO_MLFQ:
            self._sync_ready_queue()
            level = next(
                index
                for index, queue in enumerate(self.mlfq_queues)
                if queue
            )
            process = self.mlfq_queues[level].pop(0)
            self._sync_ready_queue()
            return process, level
        if self.current_algo == ALGO_PRIORITY:
            self.ready_queue.sort(key=lambda process: process.priority)
        return self.ready_queue.pop(0), None

    def _boost_mlfq(self, interrupted=None):
        queued = [process for queue in self.mlfq_queues for process in queue]
        self.mlfq_queues = [[] for _ in self.mlfq_quantums]
        for process in queued:
            process.add_waiting_time(self.time - process.last_ready_time)
            process.last_ready_time = self.time
            self.mlfq_queues[0].append(process)
        if interrupted is not None:
            interrupted.last_ready_time = self.time
            interrupted.transition_to(Process.READY)
            self.mlfq_queues[0].append(interrupted)
        self._sync_ready_queue()

    def _start_io(self, process, level):
        wake_time = process.request_io(self.time)
        heapq.heappush(
            self.blocked,
            (wake_time, self._io_event_sequence, process, level),
        )
        self._io_event_sequence += 1

    def _clear_running(self):
        self.running_process = None
        self.running_algorithm = None
        self.running_level = None

    def tick(self):
        self._process_events_through(self.time)

        if self.running_process is None:
            if not self.ready_queue:
                self.time += 1
                self._process_events_through(self.time)
                return False
            self.running_process, level = self._select_process()
            self.running_algorithm = self.current_algo
            self.running_level = level
            self.running_process.add_waiting_time(
                self.time - self.running_process.last_ready_time
            )
            self.running_process.start(self.time)

        process = self.running_process
        algorithm = self.running_algorithm
        if algorithm == ALGO_MLFQ:
            level = self.running_level
            until_boost = self.mlfq_boost_interval - (
                self.time % self.mlfq_boost_interval
            )
            duration = min(self.mlfq_quantums[level], process.remaining_time, until_boost)
        elif algorithm == ALGO_PRIORITY:
            duration = min(self.quantum, process.remaining_time)
        else:
            duration = min(self.quantum, process.remaining_time)
        until_io = process.cpu_time_until_io()
        if until_io is not None:
            duration = min(duration, until_io)

        process.execute_cpu(duration, self.time)
        self.time += duration
        self._process_events_through(self.time)

        io_due = process.cpu_time_until_io() == 0
        at_mlfq_boost = (
            algorithm == ALGO_MLFQ
            and self.time % self.mlfq_boost_interval == 0
        )
        if io_due:
            self._start_io(process, self.running_level)
            self._clear_running()
            if at_mlfq_boost and self.current_algo == ALGO_MLFQ:
                self._boost_mlfq()
            return False

        if process.is_finished():
            self.completed.append(process)
            self._clear_running()
            if at_mlfq_boost and self.current_algo == ALGO_MLFQ:
                self._boost_mlfq()
            return True

        if algorithm == ALGO_PRIORITY:
            # Non-preemptive: retain the running process across tick calls.
            return False

        level = self.running_level
        self._clear_running()
        if algorithm == ALGO_MLFQ and self.current_algo != ALGO_MLFQ:
            # A policy change during the quantum migrates the released process
            # into the currently selected policy's ready structure.
            process.last_ready_time = self.time
            process.transition_to(Process.READY)
            self.ready_queue.append(process)
        elif algorithm == ALGO_MLFQ and at_mlfq_boost:
            self._boost_mlfq(interrupted=process)
        elif algorithm == ALGO_MLFQ:
            process.last_ready_time = self.time
            process.transition_to(Process.READY)
            next_level = min(level + 1, len(self.mlfq_queues) - 1)
            self.mlfq_queues[next_level].append(process)
            self._sync_ready_queue()
        else:
            process.last_ready_time = self.time
            process.transition_to(Process.READY)
            if self.current_algo == ALGO_MLFQ:
                self.mlfq_queues[0].append(process)
                self._sync_ready_queue()
            else:
                self.ready_queue.append(process)
        return False

    def is_episode_done(self):
        return (
            self.running_process is None
            and not self.ready_queue
            and not self.pending
            and not self.blocked
        )


if __name__ == "__main__":
    simulator = SimulatorCore(max_processes=5)
    ticks = 0
    while not simulator.is_episode_done() and ticks < 1000:
        simulator.tick()
        print(simulator.get_state_summary())
        ticks += 1
    print(
        f"\nDone after {ticks} steps, {len(simulator.completed)} processes completed."
    )

