import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "default_config.json"

def load_config():
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["model_path"] = str(ROOT / cfg["model_path"])
    cfg["database"] = str(ROOT / cfg["database"])
    cfg["snapshot_dir"] = str(ROOT / cfg["snapshot_dir"])
    return cfg
