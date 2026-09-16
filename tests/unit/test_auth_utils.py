"""测试密码哈希与JWT。"""
from __future__ import annotations
import time
import pytest
from lumos.api.auth_utils import (
    hash_password, verify_password,
    create_token_pair, decode_token,
)
from lumos.errors import LumosError


def test_hash_and_verify():
    h = hash_password("hunter2")
    assert verify_password("hunter2", h)
    assert not verify_password("wrong", h)


def test_jwt_roundtrip():
    pair = create_token_pair("user-1", secret="s", access_ttl=60, refresh_ttl=120)
    assert pair.access_token and pair.refresh_token
    decoded = decode_token(pair.access_token, secret="s", expected_type="access")
    assert decoded["sub"] == "user-1"


def test_jwt_wrong_type():
    pair = create_token_pair("u", secret="s", access_ttl=60, refresh_ttl=120)
    with pytest.raises(Exception):
        decode_token(pair.refresh_token, secret="s", expected_type="access")


def test_jwt_expired():
    pair = create_token_pair("u", secret="s", access_ttl=-1, refresh_ttl=120)
    with pytest.raises(Exception, match="expired|Expired"):
        decode_token(pair.access_token, secret="s", expected_type="access")


def test_jwt_wrong_secret():
    pair = create_token_pair("u", secret="s1", access_ttl=60, refresh_ttl=120)
    with pytest.raises(Exception):
        decode_token(pair.access_token, secret="s2", expected_type="access")