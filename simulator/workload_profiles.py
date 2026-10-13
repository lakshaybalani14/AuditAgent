"""Seeded synthetic workload profiles for the scheduler simulator.

SimulatorCore can call generate_process_specs(profile_name, count, rng)
when creating an episode. This module returns Process constructor fields,
so it does not depend on SimulatorCore internals.
"""

PROFILE_DESCRIPTIONS = {
    "legacy_random": "Original arrivals 0-20, bursts 2-15, and 30% I/O-bound labels.",
    "light_load": "Short jobs with arrivals spread over a longer time window.",
    "bursty_arrivals": "Most jobs arrive together, with a smaller later burst.",
    "cpu_heavy": "Longer bursts and mostly CPU-bound process labels.",
    "short_job_heavy": "Mostly short bursts with mixed process labels.",
    "io_heavy": "Mostly I/O-bound process labels with short-to-medium bursts.",
    "long_job_heavy": "Long bursts with mixed process labels.",
}

PROFILE_NAMES = tuple(PROFILE_DESCRIPTIONS)


def normalize_workload_profiles(value=None):
    """Return a validated tuple of profile names from a sequence or CLI string."""
    if value is None:
        return ("legacy_random",)

    if isinstance(value, str):
        raw_names = value.strip()
        if raw_names.lower() == "all":
            return PROFILE_NAMES
        names = tuple(name.strip() for name in raw_names.split(",") if name.strip())
    else:
        names = tuple(value)

    if not names:
        raise ValueError("At least one workload profile must be selected.")

    unknown = sorted(set(names) - set(PROFILE_NAMES))
    if unknown:
        choices = ", ".join(PROFILE_NAMES)
        raise ValueError(
            f"Unknown workload profile(s): {', '.join(unknown)}. "
            f"Choose from: {choices}"
        )

    if len(set(names)) != len(names):
        raise ValueError("Workload profiles must not contain duplicates.")

    return names


def generate_process_specs(profile_name, count, rng):
    """Generate Process constructor dictionaries using the supplied RNG.

    The caller owns the random generator so it can reproduce an episode by
    supplying the same seed. Returned keys match simulator.Process.
    """
    if profile_name not in PROFILE_DESCRIPTIONS:
        raise ValueError(f"Unknown workload profile: {profile_name}")
    if count <= 0:
        raise ValueError("count must be greater than zero")
    if rng is None or not all(hasattr(rng, name) for name in ("randint", "random")):
        raise TypeError("rng must provide randint() and random() methods")

    batch = []
    for index in range(count):
        priority = rng.randint(0, 3)

        if profile_name == "legacy_random":
            arrival_time = rng.randint(0, 20)
            burst_time = rng.randint(2, 15)
            is_io_bound = rng.random() < 0.3
        elif profile_name == "light_load":
            arrival_time = rng.randint(0, max(20, 4 * count))
            burst_time = rng.randint(1, 6)
            is_io_bound = rng.random() < 0.3
        elif profile_name == "bursty_arrivals":
            if rng.random() < 0.75:
                arrival_time = rng.randint(0, 2)
            else:
                arrival_time = rng.randint(15, 20)
            burst_time = rng.randint(2, 12)
            is_io_bound = rng.random() < 0.3
        elif profile_name == "cpu_heavy":
            arrival_time = rng.randint(0, 20)
            burst_time = rng.randint(10, 25)
            is_io_bound = rng.random() < 0.05
        elif profile_name == "short_job_heavy":
            arrival_time = rng.randint(0, 20)
            burst_time = rng.randint(1, 4)
            is_io_bound = rng.random() < 0.3
        elif profile_name == "io_heavy":
            arrival_time = rng.randint(0, 20)
            burst_time = rng.randint(2, 12)
            is_io_bound = rng.random() < 0.8
        else:  # long_job_heavy
            arrival_time = rng.randint(0, 20)
            burst_time = rng.randint(16, 30)
            is_io_bound = rng.random() < 0.2

        batch.append(
            {
                "pid": f"P{index}",
                "arrival_time": arrival_time,
                "burst_time": burst_time,
                "priority": priority,
                "is_io_bound": is_io_bound,
            }
        )

    return sorted(batch, key=lambda process: process["arrival_time"])
