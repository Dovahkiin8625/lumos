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
    assert "Alpha Body" not in prompt
    assert "Beta instructions" in prompt


# ---------- CRUD on disk + reload ----------


def test_add_creates_directory_and_skill_file(tmp_path: Path):
    skills_dir = tmp_path / "skills"
    mgr = SkillManager(discover_dirs=[skills_dir])
    mgr.discover()
    skill = mgr.add(
        name="brand-new",
        description="hello",
        instructions="do the thing",
    )
    assert (skills_dir / "brand-new" / "SKILL.md").is_file()
    assert skill.name == "brand-new"
    assert skill.description == "hello"
    assert "do the thing" in skill.instructions
    # in-memory state reflects the new skill
    assert mgr.get("brand-new") is not None
    assert {s.name for s in mgr.list_all()} == {"brand-new"}


def test_add_rejects_invalid_name(tmp_path: Path):
    skills_dir = tmp_path / "skills"
    mgr = SkillManager(discover_dirs=[skills_dir])
    mgr.discover()
    with pytest.raises(ValueError):
        mgr.add(name="Bad Name With Spaces")
    with pytest.raises(ValueError):
        mgr.add(name="")  # empty
    with pytest.raises(ValueError):
        mgr.add(name="-leading-dash")


def test_add_rejects_duplicate(tmp_path: Path):
    skills_dir = tmp_path / "skills"
    mgr = SkillManager(discover_dirs=[skills_dir])
    mgr.add(name="dup", description="first")
    with pytest.raises(Exception):  # already-exists error
        mgr.add(name="dup", description="second")
    # first write survived
    skill = mgr.get("dup")
    assert skill is not None
    assert skill.description == "first"


def test_update_overwrites_skill_file(tmp_path: Path):
    skills_dir = tmp_path / "skills"
    mgr = SkillManager(discover_dirs=[skills_dir])
    mgr.add(name="editable", description="v1", instructions="old body")
    updated = mgr.update(
        "editable",
        description="v2",
        instructions="new body",
        version="2.0.0",
        tags=["t1"],
    )
    assert updated.description == "v2"
    assert updated.version == "2.0.0"
    assert "new body" in updated.instructions
    assert updated.tags == ["t1"]
    # on disk reflects update
    raw = (skills_dir / "editable" / "SKILL.md").read_text(encoding="utf-8")
    assert "v2" in raw
    assert "new body" in raw


def test_update_preserves_unspecified_fields(tmp_path: Path):
    skills_dir = tmp_path / "skills"
    mgr = SkillManager(discover_dirs=[skills_dir])
    mgr.add(
        name="k", description="d", instructions="i",
        version="1.0.0", tags=["a", "b"], required_tools=["x"],
    )
    # only change instructions
    updated = mgr.update("k", instructions="i2")
    assert updated.description == "d"
    assert updated.version == "1.0.0"
    assert updated.tags == ["a", "b"]
    assert updated.required_tools == ["x"]
    assert updated.instructions == "i2"


def test_update_unknown_skill_raises(tmp_path: Path):
    skills_dir = tmp_path / "skills"
    mgr = SkillManager(discover_dirs=[skills_dir])
    with pytest.raises(Exception):
        mgr.update("ghost", description="x")


def test_remove_deletes_directory(tmp_path: Path):
    skills_dir = tmp_path / "skills"
    mgr = SkillManager(discover_dirs=[skills_dir])
    mgr.add(name="togo", description="bye")
    assert (skills_dir / "togo" / "SKILL.md").is_file()
    mgr.remove("togo")
    assert not (skills_dir / "togo").exists()
    assert mgr.get("togo") is None


def test_remove_unknown_skill_raises(tmp_path: Path):
    skills_dir = tmp_path / "skills"
    mgr = SkillManager(discover_dirs=[skills_dir])
    with pytest.raises(Exception):
        mgr.remove("ghost")


def test_reload_picks_up_external_changes(tmp_path: Path):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    mgr = SkillManager(discover_dirs=[skills_dir])
    mgr.discover()
    assert mgr.get("extern") is None
    # write a new skill directly to disk, bypassing the manager
    (skills_dir / "extern").mkdir()
    (skills_dir / "extern" / "SKILL.md").write_text(
        "---\nname: extern\ndescription: from disk\n---\nbody\n",
        encoding="utf-8",
    )
    mgr.reload()
    s = mgr.get("extern")
    assert s is not None
    assert s.description == "from disk"