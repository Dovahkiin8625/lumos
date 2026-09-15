"""Skill管理器：扫描、启用/禁用、构建系统提示词。"""
from __future__ import annotations
from pathlib import Path
from typing import Iterable
from lumos.skills.loader import Skill, parse_skill


class SkillManager:
    def __init__(self, *, discover_dirs: Iterable[str | Path]) -> None:
        self._dirs = [Path(d) for d in discover_dirs]
        self._skills: dict[str, Skill] = {}

    def discover(self) -> None:
        self._skills.clear()
        for d in self._dirs:
            if not d.exists():
                continue
            for skill_md in d.glob("*/SKILL.md"):
                try:
                    s = parse_skill(skill_md)
                    self._skills[s.name] = s
                except Exception as e:
                    import structlog
                    structlog.get_logger().warning(
                        "skill.parse_failed", path=str(skill_md), error=str(e),
                    )

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def enable(self, name: str) -> None:
        if name in self._skills:
            self._skills[name].enabled = True

    def disable(self, name: str) -> None:
        if name in self._skills:
            self._skills[name].enabled = False

    def list_all(self) -> list[Skill]:
        return list(self._skills.values())

    def list_enabled(self) -> list[Skill]:
        return [s for s in self._skills.values() if s.enabled]

    def missing_required_tools(
        self, available_tools: set[str],
    ) -> dict[str, list[str]]:
        """返回{name: missing_tools}，表示启用的skill缺少哪些依赖工具。"""
        result: dict[str, list[str]] = {}
        for s in self._skills.values():
            if not s.enabled:
                continue
            missing = [t for t in s.required_tools if t not in available_tools]
            if missing:
                result[s.name] = missing
        return result

    def build_system_prompt(self, *, base: str) -> str:
        """拼接base prompt + 启用skills的指令。"""
        parts = [base]
        for s in self.list_enabled():
            parts.append(f"\n\n## Skill: {s.name}\n{s.instructions}")
        return "".join(parts)