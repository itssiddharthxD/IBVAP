"""Application configuration loader and accessor."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from copy import deepcopy

from .exceptions import ConfigError


# Project root = parent of core/
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class AppConfig:
    """Singleton-style configuration manager."""

    _instance: Optional["AppConfig"] = None
    _data: Dict[str, Any] = {}

    def __new__(cls) -> "AppConfig":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self) -> None:
        default_path = PROJECT_ROOT / "config" / "default_config.json"
        local_path = PROJECT_ROOT / "config" / "local_config.json"

        if not default_path.exists():
            raise ConfigError(f"Default config not found: {default_path}")

        with open(default_path, "r", encoding="utf-8") as f:
            self._data = json.load(f)

        if local_path.exists():
            with open(local_path, "r", encoding="utf-8") as f:
                local = json.load(f)
            self._deep_update(self._data, local)

        # Ensure absolute paths relative to project root
        storage = self._data.setdefault("storage", {})
        for key in ("database_path", "snapshot_path", "recording_path"):
            if key in storage:
                p = Path(storage[key])
                if not p.is_absolute():
                    storage[key] = str((PROJECT_ROOT / p).resolve())

        # Ensure directories exist
        for key in ("snapshot_path", "recording_path"):
            path = Path(storage.get(key, ""))
            if path:
                path.mkdir(parents=True, exist_ok=True)

        log_dir = PROJECT_ROOT / "data" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _deep_update(base: dict, override: dict) -> None:
        for k, v in override.items():
            if k in base and isinstance(base[k], dict) and isinstance(v, dict):
                AppConfig._deep_update(base[k], v)
            else:
                base[k] = v

    def get(self, *keys: str, default: Any = None) -> Any:
        node = self._data
        for k in keys:
            if not isinstance(node, dict) or k not in node:
                return default
            node = node[k]
        return node

    def set(self, *keys: str, value: Any) -> None:
        if not keys:
            return
        node = self._data
        for k in keys[:-1]:
            node = node.setdefault(k, {})
        node[keys[-1]] = value

    @property
    def data(self) -> Dict[str, Any]:
        return deepcopy(self._data)

    @property
    def project_root(self) -> Path:
        return PROJECT_ROOT

    def save_local(self) -> None:
        """Persist current config to local_config.json (user overrides)."""
        local_path = PROJECT_ROOT / "config" / "local_config.json"
        with open(local_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2)


def get_config() -> AppConfig:
    return AppConfig()
