"""测试日志配置。"""
from __future__ import annotations
import json
import logging
import pytest
from lumos.logging import configure_logging, get_logger, request_id_var


def test_configure_logging_json(capsys: pytest.CaptureFixture[str]):
    configure_logging("DEBUG", json_output=True)
    log = get_logger("test")
    log.info("hello", foo="bar")
    err = capsys.readouterr().err
    record = json.loads(err.strip().split("\n")[-1])
    assert record["event"] == "hello"
    assert record["foo"] == "bar"


def test_request_id_context():
    configure_logging("INFO", json_output=True)
    log = get_logger("test")
    token = request_id_var.set("trace-123")
    try:
        assert request_id_var.get() == "trace-123"
    finally:
        request_id_var.reset(token)