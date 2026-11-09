"""Skill管理器：扫描、启用/禁用、构建系统提示词、磁盘CRUD。"""
from __future__ import annotations
import re
import shutil
from pathlib import Path
from typing import Iterable
import structlog

import frontmatter

from lumos.errors import LumosError
from lumos.skills.loader import Skill, parse_skill


_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


class InvalidSkillNameError(ValueError, LumosError):
    """技能名称格式不合法。"""


class SkillAlreadyExistsError(LumosError):
    """技能名称已存在。"""


class SkillNotFoundError(LumosError):
    """技能不存在。"""


class SkillManager:
    def __init__(self, *, discover_dirs: Iterable[str | Path]) -> None:
        self._dirs = [Path(d) for d in discover_dirs]
        self._skills: dict[str, Skill] = {}
        self._log = structlog.get_logger()

    # ------------------------------------------------------------------ scan

    def discover(self) -> None:
        """兼容旧接口；语义同 reload()。"""
        self.reload()

    def reload(self) -> None:
        """重新扫描所有配置的目录，更新内存状态。"""
        self._skills.clear()
        for d in self._dirs:
            if not d.exists():
                continue
            for skill_md in d.glob("*/SKILL.md"):
                try:
                    s = parse_skill(skill_md)
                except Exception as e:  # noqa: BLE001 — 解析失败不阻塞其他技能
                    self._log.warning(
                        "skill.parse_failed", path=str(skill_md), error=str(e),
                    )
                    continue
                self._skills[s.name] = s

    # ------------------------------------------------------------------ read

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def list_all(self) -> list[Skill]:
        return list(self._skills.values())

    def list_enabled(self) -> list[Skill]:
        return [s for s in self._skills.values() if s.enabled]

    def enable(self, name: str) -> None:
        if name in self._skills:
            self._skills[name].enabled = True

    def disable(self, name: str) -> None:
        if name in self._skills:
            self._skills[name].enabled = False

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

    # ------------------------------------------------------------------ CRUD

    @staticmethod
    def _validate_name(name: str) -> str:
        if not isinstance(name, str) or not _NAME_RE.match(name):
            raise InvalidSkillNameError(
                "skill name must match ^[a-z0-9][a-z0-9_-]{0,63}$ "
                f"(got: {name!r})",
            )
        return name

    def _target_dir(self) -> Path:
        """新增/编辑技能的落盘目录：配置的第一个目录。"""
        if not self._dirs:
            raise LumosError("no skills dirs configured")
        return self._dirs[0]

    def _write_skill_md(
        self,
        path: Path,
        *,
        name: str,
        description: str,
        version: str,
        tags: list[str],
        required_tools: list[str],
        optional_tools: list[str],
        max_steps: int | None,
        instructions: str,
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        meta: dict = {
            "name": name,
            "description": description,
            "version": version,
            "tags": tags,
            "required_tools": required_tools,
            "optional_tools": optional_tools,
        }
        if max_steps is not None:
            meta["max_steps"] = max_steps
        post = frontmatter.Post(instructions or "", **meta)
        path.write_text(frontmatter.dumps(post), encoding="utf-8")

    def add(
        self,
        *,
        name: str,
        description: str = "",
        version: str = "0.0.0",
        tags: list[str] | None = None,
        required_tools: list[str] | None = None,
        optional_tools: list[str] | None = None,
        max_steps: int | None = None,
        instructions: str = "",
    ) -> Skill:
        """新增一个技能到第一个配置的目录，并立即 reload。"""
        self._validate_name(name)
        target = self._target_dir() / name
        if target.exists():
            raise SkillAlreadyExistsError(f"skill {name!r} already exists on disk")
        self._write_skill_md(
            target / "SKILL.md",
            name=name, description=description, version=version,
            tags=list(tags or []),
            required_tools=list(required_tools or []),
            optional_tools=list(optional_tools or []),
            max_steps=max_steps,
            instructions=instructions,
        )
        self.reload()
        created = self.get(name)
        if created is None:  # 解析失败等异常
            raise LumosError(f"skill {name!r} written but could not be reloaded")
        return created

    def update(
        self,
        name: str,
        *,
        description: str | None = None,
        version: str | None = None,
        tags: list[str] | None = None,
        required_tools: list[str] | None = None,
        optional_tools: list[str] | None = None,
        max_steps: int | None = None,
        instructions: str | None = None,
    ) -> Skill:
        """对已有技能做部分更新（仅修改传入字段），并 reload。"""
        current = self.get(name)
        if current is None:
            raise SkillNotFoundError(f"skill {name!r} not found")
        self._write_skill_md(
            current.dir_path / "SKILL.md",
            name=current.name,
            description=current.description if description is None else description,
            version=current.version if version is None else version,
            tags=current.tags if tags is None else list(tags),
            required_tools=current.required_tools if required_tools is None else list(required_tools),
            optional_tools=current.optional_tools if optional_tools is None else list(optional_tools),
            max_steps=current.max_steps if max_steps is None else max_steps,
            instructions=current.instructions if instructions is None else instructions,
        )
        self.reload()
        updated = self.get(name)
        if updated is None:
            raise LumosError(f"skill {name!r} updated but could not be reloaded")
        return updated

    def remove(self, name: str) -> None:
        """删除技能目录并 reload。"""
        current = self.get(name)
        if current is None:
            raise SkillNotFoundError(f"skill {name!r} not found")
        if current.dir_path.exists():
            shutil.rmtree(current.dir_path)
        self.reload()
