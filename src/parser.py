"""YAML config loader for stage definitions."""

import logging
from pathlib import Path
import yaml
from .models import StageDefinition

logger = logging.getLogger(__name__)


def load_stage_definitions(config_path: Path) -> dict[int, StageDefinition]:
    """
    Load stage definitions from YAML config file.

    Args:
        config_path: Path to stages.yaml

    Returns:
        Dict mapping stage id (int) to StageDefinition

    Raises:
        FileNotFoundError: If config file does not exist
        ValueError: If YAML is malformed or missing required fields
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Stage config not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not raw or "stages" not in raw:
        raise ValueError(f"Invalid config: missing 'stages' key in {config_path}")

    stages = {}
    for item in raw["stages"]:
        stage = StageDefinition(**item)
        if stage.id in stages:
            raise ValueError(f"Duplicate stage id: {stage.id}")
        stages[stage.id] = stage

    if not stages:
        raise ValueError(f"No stages defined in {config_path}")

    if len(stages) != 14:
        logger.warning(
            "Expected 14 stages, found %d in %s. "
            "The project is designed for 14 stages but will work with custom counts.",
            len(stages), config_path,
        )

    return stages
