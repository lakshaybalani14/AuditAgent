"""Seeded synthetic CPU scheduling workloads.

Each call owns an isolated ``random.Random`` instance and returns fresh
``Process`` objects that can be passed to any scheduler.
"""

import random

from process import IORequest, Process


SCENARIOS = (
    "short_jobs",
    "long_jobs",
    "bursty_arrivals",
    "mixed_cpu_io",
    "sustained_high_priority",
)

_DEFAULTS = {
    "short_jobs": ((0, 20), (1, 5), (0, 3), 0.15),
    "long_jobs": ((0, 20), (10, 30), (0, 3), 0.15),
    "bursty_arrivals": ((0, 20), (2, 15), (0, 3), 0.25),
    "mixed_cpu_io": ((0, 20), (2, 15), (0, 3), 0.5),
    "sustained_high_priority": ((0, 20), (2, 15), (0, 3), 0.25),
}


def _validate_range(name, values, minimum=0):
    try:
        low, high = values
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a pair of inclusive integer bounds") from exc
    for value in (low, high):
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError(f"{name} bounds must be integers")
        if value < minimum:
            raise ValueError(f"{name} bounds must be at least {minimum}")
    if low > high:
        raise ValueError(f"{name} lower bound must not exceed upper bound")
    return low, high


def generate_workload(
    seed,
    count=10,
    scenario="mixed_cpu_io",
    *,
    arrival_range=None,
    burst_range=None,
    priority_range=None,
    io_probability=None,
    io_request_count_range=(0, 2),
    io_duration_range=(1, 5),
):
    """Create a deterministic workload of ``Process`` objects.

    Ranges use inclusive bounds. Lower numeric priorities are higher priority.
    ``bursty_arrivals`` produces three arrival clusters; other profiles sample
    arrivals uniformly. I/O offsets are cumulative CPU service ticks.
    """
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise TypeError("seed must be an integer")
    if not isinstance(count, int) or isinstance(count, bool):
        raise TypeError("count must be an integer")
    if count < 0:
        raise ValueError("count must be non-negative")
    if scenario not in _DEFAULTS:
        raise ValueError(f"unknown scenario {scenario!r}; expected one of {SCENARIOS}")

    defaults = _DEFAULTS[scenario]
    arrivals = _validate_range("arrival_range", arrival_range or defaults[0])
    bursts = _validate_range("burst_range", burst_range or defaults[1], minimum=1)
    priorities = _validate_range("priority_range", priority_range or defaults[2])
    io_counts = _validate_range("io_request_count_range", io_request_count_range)
    io_durations = _validate_range("io_duration_range", io_duration_range, minimum=1)
    probability = defaults[3] if io_probability is None else io_probability
    if isinstance(probability, bool) or not isinstance(probability, (int, float)):
        raise TypeError("io_probability must be a number between 0 and 1")
    if not 0 <= probability <= 1:
        raise ValueError("io_probability must be between 0 and 1")

    rng = random.Random(seed)
    result = []
    arrival_low, arrival_high = arrivals
    for index in range(count):
        if scenario == "bursty_arrivals" and arrival_low < arrival_high:
            cluster = index % 3
            anchor = arrival_low + (arrival_high - arrival_low) * cluster // 2
            arrival = min(arrival_high, anchor + rng.randint(0, min(2, arrival_high - anchor)))
        else:
            arrival = rng.randint(*arrivals)
        burst = rng.randint(*bursts)

        if scenario == "sustained_high_priority" and priorities[1] > priorities[0]:
            # Keep a stream of highest-priority arrivals while retaining some
            # lower-priority work for starvation/fairness experiments.
            priority = priorities[0] if index % 4 else rng.randint(priorities[0] + 1, priorities[1])
        else:
            priority = rng.randint(*priorities)

        requests = []
        if burst > 1 and rng.random() < probability:
            max_requests = min(io_counts[1], burst - 1)
            min_requests = min(io_counts[0], max_requests)
            request_count = rng.randint(min_requests, max_requests)
            offsets = sorted(rng.sample(range(1, burst), request_count))
            requests = [
                IORequest(offset, rng.randint(*io_durations)) for offset in offsets
            ]
        result.append(
            Process(
                pid=f"P{index}",
                arrival_time=arrival,
                burst_time=burst,
                priority=priority,
                io_requests=requests,
            )
        )
    return sorted(result, key=lambda process: (process.arrival_time, str(process.pid)))
