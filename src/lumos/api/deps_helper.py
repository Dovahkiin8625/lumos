"""配置助手：访问app.state。"""
from __future__ import annotations
from fastapi import Request


def get_jwt_secret() -> str:
    from lumos.config import get_config
    return get_config().auth.jwt_secret


def get_provider(request: Request):
    return request.app.state.provider


def get_tool_registry(request: Request):
    return request.app.state.tool_registry


def get_skill_manager(request: Request):
    return request.app.state.skill_manager


def get_mcp_manager(request: Request):
    return request.app.state.mcp_manager
