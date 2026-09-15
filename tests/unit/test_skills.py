"""测试Skills加载与管理。"""
from __future__ import annotations
from pathlib import Path
import textwrap
import pytest
from lumos.skills.loader import parse_skill
from lumos.skills.manager import SkillManager


@pytest.fixture
def skills_dir(tmp_path: Path) -> Path:
    d = tmp_path / "skills"
    d.mkdir()
    skill_a = d / "alpha"
    skill_a.mkdir()
    (skill_a / "SKILL.md").write_text(textwrap.dedent("""\
        ---
        name: alpha
        description: First skill
        version: 1.0.0
        tags: [t1]
        required_tools: []
        optional_tools: []
        max_steps: null
        ---

        # Alpha Body

        Use this for X.
    """), encoding="utf-8")
    skill_b = d / "beta"
    skill_b.mkdir()
    (skill_b / "SKILL.md").write_text(textwrap.dedent("""\
        ---
        name: beta
        description: Second skill
        required_tools: [datetime_now]
        ---

        Beta instructions.
    """), encoding="utf-8")
    return d


def test_parse_skill(skills_dir: Path):
    skill = parse_skill(skills_dir / "alpha" / "SKILL.md")
    assert skill.name == "alpha"
    assert skill.description == "First skill"
    assert "Alpha Body" in skill.instructions
    assert "Use this for X" in skill.instructions


def test_skill_manager_discover(skills_dir: Path):
    mgr = SkillManager(discover_dirs=[skills_dir])
    mgr.discover()
    names = {s.name for s in mgr.list_all()}
    assert names == {"alpha", "beta"}


def test_skill_manager_enable_disable(skills_dir: Path):
    mgr = SkillManager(discover_dirs=[skills_dir])
    mgr.discover()
    mgr.disable("alpha")
    enabled = {s.name for s in mgr.list_enabled()}
    assert "alpha" not in enabled
    assert "beta" in enabled


def test_build_system_prompt(skills_dir: Path):
    mgr = SkillManager(discover_dirs=[skills_dir])
    mgr.discover()
    prompt = mgr.build_system_prompt(base="BASE PROMPT")
    assert "BASE PROMPT" in prompt
    assert "alpha" in prompt.lower() or "First skill" in prompt


def test_build_system_prompt_filters_disabled(skills_dir: Path):
    mgr = SkillManager(discover_dirs=[skills_dir])
    mgr.discover()
    mgr.disable("alpha")
    prompt = mgr.build_system_prompt(base="BASE")
    assert "First skill" not in prompt
    assert "Second skill" in prompt