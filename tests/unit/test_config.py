"""测试配置加载。"""
from pathlib import Path
import os
import pytest
from lumos.config import LumosConfig, load_config


def test_load_config_from_yaml(tmp_path: Path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("""
server:
  host: 127.0.0.1
  port: 8000
provider:
  type: openai_compat
  base_url: https://api.example.com/v1
  api_key: test-key
  model: gpt-test
db:
  url: sqlite+aiosqlite:///./test.db
""", encoding="utf-8")
    cfg = load_config(cfg_file)
    assert cfg.server.host == "127.0.0.1"
    assert cfg.server.port == 8000
    assert cfg.provider.type == "openai_compat"
    assert cfg.provider.api_key == "test-key"
    assert cfg.provider.model == "gpt-test"
    assert cfg.db.url == "sqlite+aiosqlite:///./test.db"


def test_env_var_expansion(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MY_KEY", "secret-xyz")
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("""
provider:
  type: openai_compat
  base_url: https://api.example.com/v1
  api_key: ${MY_KEY}
  model: gpt-test
""", encoding="utf-8")
    cfg = load_config(cfg_file)
    assert cfg.provider.api_key == "secret-xyz"


def test_missing_required_field_raises(tmp_path: Path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("server:\n  port: 8000\n", encoding="utf-8")
    with pytest.raises(ValueError, match="provider"):
        load_config(cfg_file)