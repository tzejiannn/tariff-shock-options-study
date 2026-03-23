import yaml
from pathlib import Path

_CONFIG_PATH = Path(__file__).parent / "settings.yaml"


def _load() -> dict:
    with open(_CONFIG_PATH) as f:
        return yaml.safe_load(f)


cfg = _load()