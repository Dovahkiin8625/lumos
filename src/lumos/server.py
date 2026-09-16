"""生产服务器启动入口。"""
from __future__ import annotations
import argparse
import uvicorn
from pathlib import Path
from lumos.config import load_config, set_config
from lumos.api.app import create_app


def run(config_path: str | Path) -> None:
    cfg = load_config(config_path)
    set_config(cfg)
    app = create_app(cfg)
    uvicorn.run(
        app, host=cfg.server.host, port=cfg.server.port,
        log_level=cfg.log_level.lower(),
    )