"""pytest全局fixture。"""
from __future__ import annotations
import asyncio
from pathlib import Path
import pytest


@pytest.fixture
def tmp_config_file(tmp_path: Path) -> Path:
    """返回临时配置文件的fixture。"""
    return tmp_path / "config.yaml"