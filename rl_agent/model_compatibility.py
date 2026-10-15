"""Guards against mixing DQN checkpoints across learning specifications."""

import json
from pathlib import Path

try:
    from .scheduler_env import LEARNING_SPEC_VERSION
except ImportError:
    from scheduler_env import LEARNING_SPEC_VERSION


def _learning_spec_for_model(model_path):
    model_directory = Path(model_path).parent
    for name in ("training_metadata.json", "learning_spec.json"):
        metadata_path = model_directory / name
        if not metadata_path.exists():
            continue
        try:
            document = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Cannot read checkpoint metadata at {metadata_path}") from exc
        return document.get("learning_spec", document), metadata_path
    return None, None


def validate_resume_metadata(model_path):
    """Reject absent or old metadata before loading an incompatible replay buffer."""
    spec, metadata_path = _learning_spec_for_model(model_path)
    version = spec.get("version") if spec else None
    if version != LEARNING_SPEC_VERSION:
        where = f" ({metadata_path})" if metadata_path else ""
        raise ValueError(
            f"Cannot resume {model_path}{where}: checkpoint learning-spec version "
            f"{version!r} is incompatible with version {LEARNING_SPEC_VERSION}. "
            "Start a new run in a separate output directory; keep the old model "
            "for comparison."
        )
    return spec


def validate_model_environment(model, model_path, env):
    """Give a readable error when inference uses a checkpoint from another spec."""
    spec, metadata_path = _learning_spec_for_model(model_path)
    version = spec.get("version") if spec else None
    if version is not None and version != LEARNING_SPEC_VERSION:
        raise ValueError(
            f"Model {model_path} uses learning-spec version {version}; this code "
            f"uses version {LEARNING_SPEC_VERSION}. Train and evaluate a new "
            "checkpoint from the new environment."
        )
    if model.observation_space.shape != env.observation_space.shape:
        old_shape = model.observation_space.shape
        new_shape = env.observation_space.shape
        raise ValueError(
            f"Model {model_path} expects observations shaped {old_shape}, while "
            f"the current environment returns {new_shape}. Use the new "
            "best_model.zip or trained_model.zip checkpoint."
        )
    if model.action_space.n != env.action_space.n:
        raise ValueError(
            f"Model {model_path} has {model.action_space.n} actions, but the "
            f"current environment has {env.action_space.n}."
        )
    return metadata_path
