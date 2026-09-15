"""SKILL.md解析。"""
from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class Skill:
    name: str
    description: str
    version: str
    tags: list[str]
    required_tools: list[str]
    optional_tools: list[str]
    max_steps: int | None
    instructions: str
    dir_path: Path
    enabled: bool = True


def parse_skill(path: Path) -> Skill:
    """从SKILL.md文件解析Skill。"""
    import frontmatter
    post = frontmatter.load(path)
    meta = post.metadata
    return Skill(
        name=meta.get("name", path.parent.name),
        description=meta.get("description", ""),
        version=meta.get("version", "0.0.0"),
        tags=list(meta.get("tags", []) or []),
        required_tools=list(meta.get("required_tools", []) or []),
        optional_tools=list(meta.get("optional_tools", []) or []),
        max_steps=meta.get("max_steps"),
        instructions=post.content.strip(),
        dir_path=path.parent,
        enabled=meta.get("enabled", True),
    )