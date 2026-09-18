"""
process.py — Defines the Process data class.

Holds data only. No scheduling logic lives here — that belongs in
scheduler_algorithms.py and simulator_core.py.
"""


class Process:
    def __init__(self, pid, arrival_time, burst_time, priority=0, is_io_bound=False):
        self.pid = pid
        self.arrival_time = arrival_time
        self.burst_time = burst_time
        self.priority = priority
        self.is_io_bound = is_io_bound

        # Mutable runtime state
        self.remaining_time = burst_time
        self.start_time = None
        self.completion_time = None
        self.waiting_time = 0
        # Used to compute wait-time increments as time passes while queued.
        # Reset every time the process re-enters the ready queue.
        self.last_ready_time = arrival_time

    def is_finished(self):
        return self.remaining_time <= 0

    def __repr__(self):
        return (
            f"Process(pid={self.pid!r}, arrival_time={self.arrival_time}, "
            f"burst_time={self.burst_time}, remaining_time={self.remaining_time}, "
            f"priority={self.priority}, is_io_bound={self.is_io_bound}, "
            f"start_time={self.start_time}, completion_time={self.completion_time}, "
            f"waiting_time={self.waiting_time}, last_ready_time={self.last_ready_time})"
        )


def generate_sample_processes():
    """Fixed, hand-picked processes for manual testing only.
    NOT used by the RL environment (that uses randomized batches from
    SimulatorCore._generate_process_batch)."""
    return [
        Process(pid="P1", arrival_time=0, burst_time=5, priority=1, is_io_bound=False),
        Process(pid="P2", arrival_time=1, burst_time=3, priority=2, is_io_bound=True),
        Process(pid="P3", arrival_time=2, burst_time=8, priority=0, is_io_bound=False),
        Process(pid="P4", arrival_time=4, burst_time=2, priority=3, is_io_bound=True),
    ]


if __name__ == "__main__":
    for p in generate_sample_processes():
        print(p)
