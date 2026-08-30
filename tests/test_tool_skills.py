"""Acceptance oracle for `skills/tools/*.md`.

One skill file per capability, invariant across agents. The purpose-specific
part of using a tool lives in the contract; this is the part that is true no
matter who is holding it.

The point of the oracle: AgentAgent composes a skill set by looking up the tools
it granted, so a missing or stale file is a silent gap in what an agent knows.
These checks make that gap loud.

Written to judge generated output. Every check is mechanical, so a file can be
produced by a cheap model and rejected here rather than reviewed by hand.

Run standalone: python tests/test_tool_skills.py
Or under pytest: python -m pytest tests/test_tool_skills.py -v
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from psyki import manifest as m  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills" / "tools"

#: Required, in this order. Fixed so composition is a concatenation rather than
#: a parse — AgentAgent should never have to guess where the failure table is.
SECTIONS = ["Purpose", "Preconditions", "Procedure", "Failures", "Refuse", "Emits"]

FRONT_KEYS = ["tool", "tool_version", "skill_version", "classes", "effects"]

#: These are read by the small local models running the implement loop, not by a
#: person. Long means unread. The three hand-written exemplars sit at 350-440.
MAX_WORDS = 700


def _manifest():
    return m.Manifest.load(ROOT / m.MANIFEST_PATH)


def _skill_files() -> list[Path]:
    return sorted(SKILLS.glob("*.md"))


def _split(path: Path) -> tuple[dict[str, object], str]:
    """Front matter and body. Hand-parsed: no yaml dependency, and the format is
    deliberately narrow enough not to need one."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise AssertionError(f"{path.name}: no front matter")
    _, fm, body = text.split("---\n", 2)
    meta: dict[str, object] = {}
    for line in fm.strip().splitlines():
        if ":" not in line:
            raise AssertionError(f"{path.name}: bad front matter line {line!r}")
        key, _, value = line.partition(":")
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            meta[key.strip()] = [v.strip() for v in value[1:-1].split(",") if v.strip()]
        else:
            meta[key.strip()] = value
    return meta, body


def _sections(body: str) -> dict[str, str]:
    out: dict[str, str] = {}
    current = None
    buf: list[str] = []
    for line in body.splitlines():
        if line.startswith("## "):
            if current:
                out[current] = "\n".join(buf).strip()
            current = line[3:].strip()
            buf = []
        elif current:
            buf.append(line)
    if current:
        out[current] = "\n".join(buf).strip()
    return out


# ------------------------------------------------------------ coverage

def test_skills_directory_exists():
    """Existence IS the property — the oracle has nothing to judge otherwise."""
    assert SKILLS.is_dir(), f"{SKILLS} missing"
    assert _skill_files(), "no skill files"


def test_every_tool_has_a_skill():
    manifest = _manifest()
    have = {p.stem for p in _skill_files()}
    missing = set(manifest.tool_names) - have
    assert not missing, f"tools without a skill: {sorted(missing)}"


def test_every_skill_names_a_real_tool():
    """A skill for a tool that does not exist is dead weight AgentAgent would
    still compose into a prompt."""
    manifest = _manifest()
    known = set(manifest.tool_names)
    for path in _skill_files():
        assert path.stem in known, f"{path.name} names no tool in the manifest"


def test_filename_matches_the_declared_tool():
    for path in _skill_files():
        meta, _ = _split(path)
        assert meta["tool"] == path.stem, (
            f"{path.name} declares tool {meta['tool']!r}"
        )


# ------------------------------------------------------------ front matter

def test_front_matter_carries_every_required_key():
    for path in _skill_files():
        meta, _ = _split(path)
        for key in FRONT_KEYS:
            assert key in meta, f"{path.name}: missing {key!r}"


def test_declared_version_matches_the_manifest():
    """A skill describing v1.0.0 of a tool is wrong after a bump. Pairing them
    here makes staleness a failing test instead of a silent misinstruction."""
    manifest = _manifest()
    for path in _skill_files():
        meta, _ = _split(path)
        tool = manifest.tool(path.stem)
        assert meta["tool_version"] == tool.version, (
            f"{path.name}: skill describes {meta['tool_version']}, "
            f"manifest has {tool.version}"
        )


def test_declared_classes_and_effects_match_the_manifest():
    manifest = _manifest()
    for path in _skill_files():
        meta, _ = _split(path)
        tool = manifest.tool(path.stem)
        assert set(meta["classes"]) == set(tool.classes), path.name
        assert set(meta["effects"]) == set(tool.effects), path.name


def test_skill_version_is_semver():
    for path in _skill_files():
        meta, _ = _split(path)
        assert re.fullmatch(r"\d+\.\d+\.\d+", str(meta["skill_version"])), path.name


# ------------------------------------------------------------ shape

def test_every_section_is_present_and_in_order():
    for path in _skill_files():
        _, body = _split(path)
        found = [line[3:].strip() for line in body.splitlines()
                 if line.startswith("## ")]
        assert found == SECTIONS, f"{path.name}: sections are {found}"


def test_no_section_is_empty():
    for path in _skill_files():
        _, body = _split(path)
        for name, content in _sections(body).items():
            assert len(content.split()) >= 5, f"{path.name}: {name} is a stub"


def test_purpose_is_one_sentence():
    for path in _skill_files():
        _, body = _split(path)
        purpose = _sections(body)["Purpose"]
        assert purpose.count(".") <= 1, f"{path.name}: Purpose is not one sentence"
        assert len(purpose.split()) <= 30, f"{path.name}: Purpose is too long"


def test_procedure_is_numbered_steps():
    for path in _skill_files():
        _, body = _split(path)
        steps = [ln for ln in _sections(body)["Procedure"].splitlines()
                 if re.match(r"^\d+\.\s", ln)]
        assert len(steps) >= 3, f"{path.name}: Procedure has {len(steps)} steps"


def test_failures_is_a_three_column_table_with_real_rows():
    """The failure table is the part a weak model actually needs. A skill with
    a thin one has described the happy path and called it a procedure."""
    for path in _skill_files():
        _, body = _split(path)
        rows = [ln for ln in _sections(body)["Failures"].splitlines()
                if ln.strip().startswith("|") and not set(ln) <= set("|- ")]
        assert len(rows) >= 4, f"{path.name}: {len(rows) - 1} failure rows"
        for row in rows:
            cells = [c for c in row.strip().strip("|").split("|")]
            assert len(cells) == 3, f"{path.name}: bad row {row!r}"
            assert all(c.strip() for c in cells), f"{path.name}: empty cell in {row!r}"


def test_refuse_and_preconditions_are_bulleted():
    for path in _skill_files():
        _, body = _split(path)
        for name in ("Preconditions", "Refuse"):
            bullets = [ln for ln in _sections(body)[name].splitlines()
                       if ln.strip().startswith("- ")]
            assert len(bullets) >= 3, f"{path.name}: {name} has {len(bullets)} bullets"


def test_file_is_short_enough_to_be_read():
    for path in _skill_files():
        words = len(path.read_text(encoding="utf-8").split())
        assert words <= MAX_WORDS, f"{path.name}: {words} words, cap {MAX_WORDS}"


# ------------------------------------------------------------ content invariants

def test_egress_tools_say_their_output_is_untrusted():
    """Every tool that reaches outside returns text the Emissary must convert.
    A skill that omits this teaches an agent to read a fetched body as
    instruction, which is the injection path this architecture exists to close."""
    manifest = _manifest()
    for path in _skill_files():
        if "EGRESS" not in manifest.tool(path.stem).effects:
            continue
        text = path.read_text(encoding="utf-8").lower()
        assert "untrusted" in text, f"{path.name}: EGRESS tool never says untrusted"


def test_provisioned_only_skills_do_not_address_meta_agents():
    """A provisioned agent has no business being told how PSY or the Emissary
    behave; naming them invites an attempt to influence them."""
    manifest = _manifest()
    allowed = {"llm_prompt"}  # states the boundary explicitly, on purpose
    for path in _skill_files():
        tool = manifest.tool(path.stem)
        if m.INTERNAL in tool.classes or path.stem in allowed:
            continue
        text = path.read_text(encoding="utf-8")
        for name in ("PSY", "Emissary", "TaskMaster"):
            assert name not in text, f"{path.name} names {name}"


def test_no_placeholder_text_survived():
    banned = ["TODO", "TBD", "FIXME", "lorem ipsum", "<tool>", "XXX",
              "as appropriate", "etc."]
    for path in _skill_files():
        text = path.read_text(encoding="utf-8")
        for token in banned:
            assert token.lower() not in text.lower(), f"{path.name}: {token!r}"


def test_skills_do_not_duplicate_the_manifest_description():
    """The manifest says what a tool is. The skill says how to use it. A skill
    that restates the description has added nothing."""
    manifest = _manifest()
    for path in _skill_files():
        desc = manifest.tool(path.stem).description.strip().rstrip(".")
        if len(desc) < 40:
            continue
        assert desc.lower() not in path.read_text(encoding="utf-8").lower(), \
            f"{path.name} copies the manifest description verbatim"


# ------------------------------------------------------------ runner

def _main() -> int:
    tests = [(n, o) for n, o in sorted(globals().items())
             if n.startswith("test_") and callable(o)]
    failures = 0
    for name, fn in tests:
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            failures += 1
            print(f"  FAIL  {name}: {e}")
        else:
            print(f"  pass  {name}")
    print(f"\n{'all green' if not failures else f'{failures} failed'} "
          f"({len(tests)} tests)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_main())
