"""测试 .env 自动加载。"""
from __future__ import annotations
from pathlib import Path
import textwrap

import pytest

from lumos.dotenv import load_dotenv


def test_load_dotenv_reads_simple_pairs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("FOO_TEST_KEY", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        textwrap.dedent("""\
            FOO_TEST_KEY=hello-world
            BAR_TEST_KEY=plainvalue
        """),
        encoding="utf-8",
    )
    loaded = load_dotenv(env_file, override=False)
    assert "FOO_TEST_KEY" in loaded
    assert "BAR_TEST_KEY" in loaded
    # env vars are now populated
    import os
    assert os.environ["FOO_TEST_KEY"] == "hello-world"
    assert os.environ["BAR_TEST_KEY"] == "plainvalue"


def test_load_dotenv_strips_comments_and_blanks(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("X_TEST_KEY", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        textwrap.dedent("""\
            # this is a comment
            X_TEST_KEY=value1

            # another comment
            Y_TEST_KEY=value2
        """),
        encoding="utf-8",
    )
    load_dotenv(env_file, override=False)
    import os
    assert os.environ["X_TEST_KEY"] == "value1"
    assert os.environ["Y_TEST_KEY"] == "value2"


def test_load_dotenv_handles_quoted_values(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("Z_TEST_KEY", raising=False)
    monkeypatch.delenv("W_TEST_KEY", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        'Z_TEST_KEY="with spaces"\n'
        "W_TEST_KEY='single quoted'\n",
        encoding="utf-8",
    )
    load_dotenv(env_file, override=False)
    import os
    assert os.environ["Z_TEST_KEY"] == "with spaces"
    assert os.environ["W_TEST_KEY"] == "single quoted"


def test_load_dotenv_does_not_override_existing(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("EXISTING_KEY", "preset")
    env_file = tmp_path / ".env"
    env_file.write_text("EXISTING_KEY=from-file\n", encoding="utf-8")
    load_dotenv(env_file, override=False)
    import os
    assert os.environ["EXISTING_KEY"] == "preset"


def test_load_dotenv_override_true_does_override(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OVERRIDE_KEY", "preset")
    env_file = tmp_path / ".env"
    env_file.write_text("OVERRIDE_KEY=from-file\n", encoding="utf-8")
    load_dotenv(env_file, override=True)
    import os
    assert os.environ["OVERRIDE_KEY"] == "from-file"


def test_load_dotenv_missing_file_is_noop(tmp_path: Path):
    # should not raise; returns empty set
    loaded = load_dotenv(tmp_path / "nope.env")
    assert loaded == set()


def test_load_dotenv_ignores_malformed_lines(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("GOOD_KEY", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "no-equals-sign-line\n"
        "GOOD_KEY=ok\n"
        "=missing-key\n",
        encoding="utf-8",
    )
    load_dotenv(env_file, override=False)
    import os
    assert os.environ["GOOD_KEY"] == "ok"


def test_load_dotenv_strips_inline_comment_unquoted(tmp_path: Path, monkeypatch):
    """`KEY=value # comment` → KEY 取 ``value``，注释部分不计入值。"""
    monkeypatch.delenv("COMMENT_KEY", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "COMMENT_KEY=secret-value # this is a comment\n",
        encoding="utf-8",
    )
    load_dotenv(env_file, override=False)
    import os
    assert os.environ["COMMENT_KEY"] == "secret-value"


def test_load_dotenv_strips_inline_comment_in_double_quotes(tmp_path: Path, monkeypatch):
    """引号内的 # 是值的一部分，不应被去掉。"""
    monkeypatch.delenv("QKEY", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        'QKEY="hello # not a comment" # real comment\n',
        encoding="utf-8",
    )
    load_dotenv(env_file, override=False)
    import os
    assert os.environ["QKEY"] == "hello # not a comment"


def test_load_dotenv_strips_utf8_bom(tmp_path: Path, monkeypatch):
    """PowerShell 的 ``Set-Content -Encoding utf8`` 会写 BOM，loader 必须容忍。"""
    monkeypatch.delenv("BOM_KEY", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_bytes(b"\xef\xbb\xbfBOM_KEY=hello\n")
    load_dotenv(env_file, override=False)
    import os
    assert os.environ["BOM_KEY"] == "hello"
    assert "BOM_KEY" in os.environ


def test_find_and_load_walks_up_to_repo_root(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("UP_KEY", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("UP_KEY=value\n", encoding="utf-8")
    nested = tmp_path / "a" / "b" / "c"
    nested.mkdir(parents=True)
    from lumos.dotenv import find_and_load
    loaded = find_and_load(nested, override=False)
    assert "UP_KEY" in loaded
    import os
    assert os.environ["UP_KEY"] == "value"
