"""Process data and lifecycle model for the CPU scheduling simulator."""

from dataclasses import dataclass


class ProcessState:
    """String-valued process states, kept dependency-free for callers."""

    NEW = "NEW"
    READY = "READY"
    RUNNING = "RUNNING"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"

    ALL = frozenset({NEW, READY, RUNNING, BLOCKED, COMPLETED})


@dataclass(frozen=True)
class IORequest:
    """An I/O event after cumulative CPU service, lasting ``duration`` ticks."""

    after_cpu_time: int
    duration: int


class Process:
    """A process record with validated inputs and guarded lifecycle methods.

    The original positional constructor and public fields remain available.
    ``io_requests`` is optional and accepts ``IORequest`` objects, mappings
    with ``after_cpu_time``/``duration`` keys, or two-item tuples.
    """

    NEW = ProcessState.NEW
    READY = ProcessState.READY
    RUNNING = ProcessState.RUNNING
    BLOCKED = ProcessState.BLOCKED
    COMPLETED = ProcessState.COMPLETED

    _TRANSITIONS = {
        NEW: {READY},
        READY: {RUNNING},
        RUNNING: {READY, BLOCKED, COMPLETED},
        BLOCKED: {READY},
        COMPLETED: set(),
    }

    def __init__(
        self, pid, arrival_time, burst_time, priority=0, is_io_bound=False,
        io_requests=None,
    ):
        if not isinstance(pid, (str, int)) or isinstance(pid, bool):
            raise TypeError("pid must be a string or integer")
        if isinstance(pid, str) and not pid.strip():
            raise ValueError("pid must not be empty")
        self._validate_integer("arrival_time", arrival_time, minimum=0)
        self._validate_integer("burst_time", burst_time, minimum=1)
        self._validate_integer("priority", priority, minimum=0)
        if not isinstance(is_io_bound, bool):
            raise TypeError("is_io_bound must be a bool")

        self.pid = pid
        self.arrival_time = arrival_time
        self.burst_time = burst_time
        self.priority = priority
        self.io_requests = self._normalize_io_requests(io_requests, burst_time)
        self.is_io_bound = is_io_bound or bool(self.io_requests)

        self.remaining_time = burst_time
        self._state = ProcessState.NEW
        self.start_time = None
        self.completion_time = None
        self.waiting_time = 0
        self.response_time = None
        self.turnaround_time = None
        self.cpu_execution_time = 0
        self.io_time = 0
        self.next_io_request_index = 0
        self.io_completion_time = None
        # Existing schedulers use this timestamp when re-queuing a process.
        self.last_ready_time = arrival_time

    @staticmethod
    def _validate_integer(name, value, minimum):
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError(f"{name} must be an integer")
        if value < minimum:
            raise ValueError(f"{name} must be at least {minimum}")

    @classmethod
    def _normalize_io_requests(cls, requests, burst_time):
        if requests is None:
            return []
        try:
            raw_requests = list(requests)
        except TypeError as exc:
            raise TypeError("io_requests must be an iterable of I/O requests") from exc

        normalized = []
        previous_cpu_time = 0
        for item in raw_requests:
            if isinstance(item, IORequest):
                request = item
            elif isinstance(item, dict):
                try:
                    request = IORequest(item["after_cpu_time"], item["duration"])
                except KeyError as exc:
                    raise ValueError(
                        "I/O mappings require after_cpu_time and duration"
                    ) from exc
            else:
                try:
                    after_cpu_time, duration = item
                    request = IORequest(after_cpu_time, duration)
                except (TypeError, ValueError) as exc:
                    raise TypeError(
                        "each I/O request must be IORequest, mapping, or pair"
                    ) from exc

            cls._validate_integer("I/O after_cpu_time", request.after_cpu_time, 1)
            cls._validate_integer("I/O duration", request.duration, 1)
            if request.after_cpu_time <= previous_cpu_time:
                raise ValueError("I/O requests must have increasing CPU offsets")
            if request.after_cpu_time >= burst_time:
                raise ValueError("I/O request must occur before CPU burst completion")
            normalized.append(request)
            previous_cpu_time = request.after_cpu_time
        return normalized

    def transition_to(self, new_state):
        """Move to a legal lifecycle state or raise ``ValueError``."""
        if new_state not in ProcessState.ALL:
            raise ValueError(f"Unknown process state: {new_state!r}")
        if new_state not in self._TRANSITIONS[self.state]:
            raise ValueError(
                f"Invalid process transition: {self.state} -> {new_state}"
            )
        self._state = new_state

    @property
    def state(self):
        """Current lifecycle state; change it through ``transition_to``."""
        return self._state

    def mark_ready(self, time=None):
        if time is not None:
            self._validate_integer("time", time, minimum=self.arrival_time)
        self.transition_to(ProcessState.READY)
        if time is not None:
            self.last_ready_time = time

    def start(self, time):
        self._validate_integer("time", time, minimum=self.arrival_time)
        self.transition_to(ProcessState.RUNNING)
        if self.start_time is None:
            self.start_time = time
            self.response_time = time - self.arrival_time

    def add_waiting_time(self, duration):
        self._validate_integer("waiting duration", duration, minimum=0)
        if self.state != ProcessState.READY:
            raise ValueError("waiting time can only accrue while READY")
        self.waiting_time += duration

    def execute_cpu(self, duration, time):
        """Run for ``duration`` ticks, updating CPU and completion accounting."""
        self._validate_integer("CPU duration", duration, minimum=1)
        self._validate_integer("time", time, minimum=self.arrival_time)
        if duration > self.remaining_time:
            raise ValueError("CPU duration exceeds remaining CPU time")
        if self.state == ProcessState.READY:
            self.start(time)
        elif self.state != ProcessState.RUNNING:
            raise ValueError("CPU execution requires a READY or RUNNING process")
        self.remaining_time -= duration
        self.cpu_execution_time += duration
        if self.remaining_time == 0:
            self.completion_time = time + duration
            self.turnaround_time = self.completion_time - self.arrival_time
            self.transition_to(ProcessState.COMPLETED)

    def block(self):
        self.transition_to(ProcessState.BLOCKED)

    @property
    def next_io_request(self):
        if self.next_io_request_index >= len(self.io_requests):
            return None
        return self.io_requests[self.next_io_request_index]

    def cpu_time_until_io(self):
        """CPU service ticks remaining until the next configured I/O event."""
        request = self.next_io_request
        if request is None:
            return None
        return request.after_cpu_time - self.cpu_execution_time

    def request_io(self, time):
        """Block at a reached I/O offset and return its scheduled wake time."""
        self._validate_integer("time", time, minimum=self.arrival_time)
        request = self.next_io_request
        if self.state != ProcessState.RUNNING or request is None:
            raise ValueError("process has no I/O request to issue")
        if request.after_cpu_time != self.cpu_execution_time:
            raise ValueError("I/O request issued at the wrong CPU execution point")
        self.io_completion_time = time + request.duration
        self.io_time += request.duration
        self.next_io_request_index += 1
        self.block()
        return self.io_completion_time

    def complete_io(self, time):
        """Wake a blocked process when its I/O completion time is reached."""
        self._validate_integer("time", time, minimum=self.arrival_time)
        if self.state != ProcessState.BLOCKED or self.io_completion_time is None:
            raise ValueError("process is not waiting for I/O")
        if time < self.io_completion_time:
            raise ValueError("I/O cannot complete before its scheduled time")
        self.io_completion_time = None
        self.mark_ready(time)

    def complete(self, time):
        """Mark a fully executed process complete at an explicit time."""
        self._validate_integer("time", time, minimum=self.arrival_time)
        if self.state == ProcessState.COMPLETED:
            if self.completion_time != time:
                raise ValueError("process is already complete at a different time")
            return
        if self.remaining_time != 0:
            raise ValueError("cannot complete a process with CPU time remaining")
        self.transition_to(ProcessState.COMPLETED)
        self.completion_time = time
        self.turnaround_time = time - self.arrival_time

    def is_finished(self):
        return self.remaining_time <= 0

    def __repr__(self):
        return (
            f"Process(pid={self.pid!r}, arrival_time={self.arrival_time}, "
            f"burst_time={self.burst_time}, remaining_time={self.remaining_time}, "
            f"priority={self.priority}, state={self.state!r}, "
            f"is_io_bound={self.is_io_bound}, start_time={self.start_time}, "
            f"completion_time={self.completion_time}, waiting_time={self.waiting_time}, "
            f"cpu_execution_time={self.cpu_execution_time}, "
            f"last_ready_time={self.last_ready_time})"
        )


def generate_sample_processes():
    """Fixed, hand-picked processes for manual testing only."""
    return [
        Process(pid="P1", arrival_time=0, burst_time=5, priority=1, is_io_bound=False),
        Process(pid="P2", arrival_time=1, burst_time=3, priority=2, is_io_bound=True),
        Process(pid="P3", arrival_time=2, burst_time=8, priority=0, is_io_bound=False),
        Process(pid="P4", arrival_time=4, burst_time=2, priority=3, is_io_bound=True),
    ]


if __name__ == "__main__":
    for process in generate_sample_processes():
        print(process)
