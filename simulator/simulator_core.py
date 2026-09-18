"""
simulator_core.py — The steppable version of the scheduler.

Unlike scheduler_algorithms.py (run one algorithm start-to-finish), this
class advances ONE TICK AT A TIME and can switch which algorithm is
active mid-run. This is the bridge that rl_agent/scheduler_env.py wraps.
"""

import random

from process import Process

ALGO_ROUND_ROBIN = 0
ALGO_PRIORITY = 1
ALGO_MLFQ = 2

STARVATION_THRESHOLD = 50  # ticks


class SimulatorCore:
    def __init__(self, max_processes=10, quantum=2):
        self.max_processes = max_processes
        self.quantum = quantum
        self.time = 0
        self.current_algo = ALGO_ROUND_ROBIN
        self.ready_queue = []
        self.pending = []
        self.completed = []
        self.reset()

    def reset(self):
        self.time = 0
        self.current_algo = ALGO_ROUND_ROBIN
        self.ready_queue = []
        self.completed = []
        self.pending = self._generate_process_batch()
        self._admit_arrivals()

    def _generate_process_batch(self):
        batch = []
        for i in range(self.max_processes):
            proc = Process(
                pid=f"P{i}",
                arrival_time=random.randint(0, 20),
                burst_time=random.randint(2, 15),
                priority=random.randint(0, 3),
                is_io_bound=random.random() < 0.3,
            )
            batch.append(proc)
        batch.sort(key=lambda p: p.arrival_time)
        return batch

    def _admit_arrivals(self):
        while self.pending and self.pending[0].arrival_time <= self.time:
            proc = self.pending.pop(0)
            proc.last_ready_time = self.time
            self.ready_queue.append(proc)

    def get_state_summary(self):
        queue_length = len(self.ready_queue)
        if queue_length > 0:
            wait_times = [self.time - p.last_ready_time for p in self.ready_queue]
            avg_wait_time = sum(wait_times) / queue_length
            max_wait_time = max(wait_times)
        else:
            avg_wait_time = 0.0
            max_wait_time = 0.0

        num_io_bound = sum(1 for p in self.ready_queue if p.is_io_bound)
        num_cpu_bound = queue_length - num_io_bound

        return {
            "time": self.time,
            "queue_length": queue_length,
            "avg_wait_time": avg_wait_time,
            "max_wait_time": max_wait_time,
            "num_io_bound": num_io_bound,
            "num_cpu_bound": num_cpu_bound,
            "current_algo": self.current_algo,
            "is_starving": max_wait_time > STARVATION_THRESHOLD,
        }

    def apply_action(self, action):
        if action == 0:
            pass  # no change
        elif action == 1:
            self.current_algo = ALGO_ROUND_ROBIN
        elif action == 2:
            self.current_algo = ALGO_PRIORITY
        elif action == 3:
            self.current_algo = ALGO_MLFQ
        elif action == 4:
            if self.ready_queue:
                longest_waiting = max(
                    self.ready_queue, key=lambda p: self.time - p.last_ready_time
                )
                longest_waiting.priority = max(0, longest_waiting.priority - 1)
        else:
            raise ValueError(f"Unknown action: {action}")

    def tick(self):
        self._admit_arrivals()

        if not self.ready_queue:
            self.time += 1
            self._admit_arrivals()
            return False

        if self.current_algo == ALGO_PRIORITY:
            self.ready_queue.sort(key=lambda p: p.priority)

        current = self.ready_queue.pop(0)
        slice_len = min(self.quantum, current.remaining_time)
        self.time += slice_len
        current.remaining_time -= slice_len

        self._admit_arrivals()

        if current.is_finished():
            current.completion_time = self.time
            current.waiting_time = (
                current.completion_time - current.arrival_time - current.burst_time
            )
            self.completed.append(current)
            return True
        else:
            current.last_ready_time = self.time
            self.ready_queue.append(current)
            return False

    def is_episode_done(self):
        return not self.ready_queue and not self.pending


if __name__ == "__main__":
    sim = SimulatorCore(max_processes=5)
    ticks = 0
    while not sim.is_episode_done() and ticks < 100:
        sim.tick()
        print(sim.get_state_summary())
        ticks += 1
    print(f"\nDone after {ticks} ticks, {len(sim.completed)} processes completed.")
