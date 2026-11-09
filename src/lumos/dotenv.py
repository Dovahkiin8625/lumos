"""极简 .env 加载器：解析 KEY=VALUE 行，注入 os.environ。

不引入第三方依赖。语义参考 python-dotenv（但不覆盖已存在的环境变量，除非显式指定）。
"""
from __future__ import annotations
import os
from pathlib import Path


def load_dotenv(path: str | Path, *, override: bool = False) -> set[str]:
    """从 .env 文件加载键值到 os.environ。

    - 跳过空行与 `#` 开头注释
    - 支持 ``KEY=value`` / ``KEY="quoted value"`` / ``KEY='single'``
    - 容忍 UTF-8 BOM（PowerShell ``Set-Content -Encoding utf8`` 会写 BOM）
    - 若 ``override=False``（默认），已存在的环境变量不会被覆盖
    - 不存在或不可读的文件静默返回空集合

    返回被设置的变量名集合（不论是新增还是覆盖）。
    """
    p = Path(path)
    if not p.is_file():
        return set()

    loaded: set[str] = set()
    text = p.read_text(encoding="utf-8-sig")  # 自动剥离 BOM
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, raw_value = line.partition("=")
        key = key.strip()
        if not key:
            continue
        value = _parse_value(raw_value)
        if not override and key in os.environ:
            continue
        os.environ[key] = value
        loaded.add(key)
    return loaded


def _parse_value(raw: str) -> str:
    """解析 ``=`` 右侧的原始串。

    规则（与 python-dotenv 一致）：
    - 若以 ``"`` 或 ``'`` 开头，取到下一个相同引号为止；引号外允许 ``#`` 注释
    - 否则值一直延伸到行尾；首个非引号 # 之后的字符视作注释丢弃
    - 未配对的引号视为普通字符
    """
    s = raw.lstrip()
    if not s:
        return ""
    quote = s[0] if s[0] in ("'", '"') else ""
    if quote:
        # 找到配对的结束引号
        end = s.find(quote, 1)
        if end < 0:
            # 未配对，整段作为值
            return s[1:]
        return s[1:end]
    # 无引号：# 之后的字符全部视作注释（允许前面的空白）
    hash_pos = _find_unquoted_hash(s)
    return s[:hash_pos].rstrip() if hash_pos >= 0 else s.rstrip()


def _find_unquoted_hash(s: str) -> int:
    """返回未在引号内的 # 的下标；不存在则返回 -1。"""
    i = 0
    while i < len(s):
        c = s[i]
        if c in ("'", '"'):
            # 跳过该引号到结束
            end = s.find(c, i + 1)
            if end < 0:
                return -1
            i = end + 1
            continue
        if c == "#":
            return i
        i += 1
    return -1


def find_and_load(start: str | Path = ".", *, override: bool = False) -> set[str]:
    """从 start 向上查找 .env，找到即加载，返回所有被设置的变量名。"""
    cur = Path(start).resolve()
    for parent in [cur, *cur.parents]:
        candidate = parent / ".env"
        if candidate.is_file():
            return load_dotenv(candidate, override=override)
    return set()
