"""Acceptance oracle for `procedures/*.md`.

The four layers and what separates them:

  tool       a capability. What may be done.
  skill      how to use one tool, invariant across agents. One per tool.
  procedure  a methodology for a piece of work. MANY per skill.
  style      a constraint on the artifact. Enforced by a linter.

A skill says how `process_run` behaves. A procedure says how *this team* runs
the gate chain — and there can be a strict one, a fast one for iteration, and a
security-heavy one for a release. Same skill, different method, selected per
contract.

That selection is the point. Toolset to skills is mechanical, a lookup.
Contract to procedure is a choice, made by AgentAgent at design time, and it is
where agent behaviour gets tuned without touching the tool or the skill.

Toolsets are DERIVED, not selected. Canon §3's "a task is its toolset" is a
least-privilege rule — a tool is provisioned only if the work necessitates it —
and a fixed bundle violates it by granting capability nobody asked for. So a
procedure declares the tools its method requires and nothing else; AgentAgent
grants the union across the procedures it selected, and the toolset is the
output of that, not an input to it.

The load-bearing check here is `test_every_used_tool_appears_in_the_method`.
Every tool in `uses` will be provisioned to every agent running this procedure,
so a tool listed and never used is an unnecessary capability granted forever.

Run standalone: python tests/test_procedures.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from psyki import manifest as m  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PROCS = ROOT / "procedures"
SKILLS = ROOT / "skills" / "tools"
GATE_COMMANDS = ROOT / "style" / "gate_commands.json"

SECTIONS = ["Purpose", "Applies to", "Uses", "Method", "Standards", "Outputs"]
FRONT_KEYS = ["procedure", "procedure_version", "uses"]
MAX_WORDS = 800


def _manifest():
    return m.Manifest.load(ROOT / m.MANIFEST_PATH)


def _files() -> list[Path]:
    return sorted(PROCS.glob("*.md"))


def _split(path: Path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise AssertionError(f"{path.name}: no front matter")
    _, fm, body = text.split("---\n", 2)
    meta: dict[str, object] = {}
    for line in fm.strip().splitlines():
        key, _, value = line.partition(":")
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            meta[key.strip()] = [v.strip() for v in value[1:-1].split(",") if v.strip()]
        else:
            meta[key.strip()] = value
    return meta, body


def _sections(body: str) -> dict[str, str]:
    out, current, buf = {}, None, []
    for line in body.splitlines():
        if line.startswith("## "):
            if current:
                out[current] = "\n".join(buf).strip()
            current, buf = line[3:].strip(), []
        elif current:
            buf.append(line)
    if current:
        out[current] = "\n".join(buf).strip()
    return out


def _all(check):
    """Collect every failure before raising.

    Written this way on purpose: the last generated batch had eight files
    diverging the same way, and a short-circuiting assert reported one. A
    systematic error should look systematic.
    """
    bad = []
    for path in _files():
        try:
            check(path)
        except AssertionError as e:
            bad.append(str(e))
    assert not bad, "\n        " + "\n        ".join(bad)


# ------------------------------------------------------------ structure

def test_procedures_directory_exists():
    assert PROCS.is_dir(), f"{PROCS} missing"
    assert _files(), "no procedure files"


def test_front_matter_carries_every_required_key():
    def check(p):
        meta, _ = _split(p)
        missing = [k for k in FRONT_KEYS if k not in meta]
        assert not missing, f"{p.name}: missing {missing}"
    _all(check)


def test_filename_matches_the_declared_procedure():
    def check(p):
        meta, _ = _split(p)
        assert meta["procedure"] == p.stem, f"{p.name}: declares {meta['procedure']!r}"
    _all(check)


def test_procedure_version_is_semver():
    def check(p):
        meta, _ = _split(p)
        assert re.fullmatch(r"\d+\.\d+\.\d+", str(meta["procedure_version"])), p.name
    _all(check)


def test_every_section_is_present_and_in_order():
    def check(p):
        _, body = _split(p)
        found = [ln[3:].strip() for ln in body.splitlines() if ln.startswith("## ")]
        assert found == SECTIONS, f"{p.name}: sections are {found}"
    _all(check)


def test_no_section_is_a_stub():
    def check(p):
        _, body = _split(p)
        for name, content in _sections(body).items():
            assert len(content.split()) >= 8, f"{p.name}: {name} is a stub"
    _all(check)


def test_purpose_is_one_sentence():
    def check(p):
        _, body = _split(p)
        purpose = _sections(body)["Purpose"]
        assert purpose.count(".") <= 1 and len(purpose.split()) <= 30, \
            f"{p.name}: Purpose is not one short sentence"
    _all(check)


def test_method_is_numbered_steps():
    def check(p):
        _, body = _split(p)
        steps = [ln for ln in _sections(body)["Method"].splitlines()
                 if re.match(r"^\d+\.\s", ln)]
        assert len(steps) >= 4, f"{p.name}: Method has {len(steps)} steps"
    _all(check)


def test_applies_to_gives_a_selection_criterion():
    """Many procedures can serve one skill, so each must say when it is the
    right one. Without that, AgentAgent has a menu and no way to order."""
    def check(p):
        _, body = _split(p)
        bullets = [ln for ln in _sections(body)["Applies to"].splitlines()
                   if ln.strip().startswith("- ")]
        assert len(bullets) >= 2, f"{p.name}: Applies to has {len(bullets)} bullets"
        text = re.sub(r"[*_`]", "", _sections(body)["Applies to"]).lower()
        assert " not " in text or "instead" in text or "rather than" in text, \
            f"{p.name}: Applies to never says when NOT to choose this one"
    _all(check)


def test_standards_are_measurable():
    """A standard nothing can check is an aspiration.

    Partial by construction: this catches the shape of measurability, and the
    shape can be faked. "Zero write operations permitted" on a read-only tool
    restates an effect; "100% of matching entries" is a tautology. Both would
    pass the numeric check. Whether a criterion is genuinely checkable stays a
    review judgement, and the restated-effect case below is the part that can
    be automated."""
    absolutes = ("zero", "no diff", "all pass", "none", "must", "never", "%")
    def check(p):
        _, body = _split(p)
        text = _sections(body)["Standards"].lower()
        assert any(a in text for a in absolutes) or re.search(r"\d", text), \
            f"{p.name}: Standards contains nothing checkable"
    _all(check)


def test_standards_do_not_restate_tool_effects():
    """A read-only tool not writing is a fact about the tool, not a standard the
    procedure upholds. Claiming it as one inflates the section with criteria
    that cannot fail."""
    manifest = _manifest()
    vacuous = {
        "WRITE": ("zero write", "no write", "without writing", "read-only"),
        "EGRESS": ("no network", "zero network", "offline only"),
        "EXECUTE": ("no execution", "zero execution", "does not execute"),
    }
    def check(p):
        meta, body = _split(p)
        held = {e for t in meta["uses"] for e in manifest.tool(t).effects}
        text = _sections(body)["Standards"].lower()
        for effect, phrases in vacuous.items():
            if effect in held:
                continue
            hits = [ph for ph in phrases if ph in text]
            assert not hits, (
                f"{p.name}: claims {hits} as a standard, but no tool in `uses` "
                f"has {effect} — that is a fact about the tools, not a standard"
            )
    _all(check)


def test_file_is_short_enough_to_be_read():
    def check(p):
        words = len(p.read_text(encoding="utf-8").split())
        assert words <= MAX_WORDS, f"{p.name}: {words} words, cap {MAX_WORDS}"
    _all(check)


# ------------------------------------------------------------ integrity

def test_uses_name_real_tools():
    manifest = _manifest()
    known = set(manifest.tool_names)
    def check(p):
        meta, _ = _split(p)
        unknown = [t for t in meta["uses"] if t not in known]
        assert not unknown, f"{p.name}: uses unknown tools {unknown}"
    _all(check)


def test_no_procedure_declares_a_toolset():
    """Toolsets are derived. A procedure declaring one is selecting a bundle,
    which grants capability no step of its method requires."""
    def check(p):
        meta, _ = _split(p)
        stray = [k for k in ("toolsets", "default_for") if k in meta]
        assert not stray, f"{p.name}: declares {stray} — toolsets are derived"
    _all(check)


def test_every_used_tool_appears_in_the_method():
    """Every tool in `uses` is provisioned to every agent that runs this. One
    listed and never used is a standing grant with no work behind it."""
    def check(p):
        meta, body = _split(p)
        method = _sections(body)["Method"]
        unused = [t for t in meta["uses"] if t not in method]
        assert not unused, f"{p.name}: uses {unused}, never used in Method"
    _all(check)


def test_every_used_tool_has_a_skill():
    """A procedure directs the use of a skill. Naming a tool with no skill file
    means the agent gets a method and no manual."""
    have = {q.stem for q in SKILLS.glob("*.md")}
    def check(p):
        meta, _ = _split(p)
        missing = [t for t in meta["uses"] if t not in have]
        assert not missing, f"{p.name}: no skill file for {missing}"
    _all(check)


def test_no_placeholder_text_survived():
    banned = ["TODO", "TBD", "FIXME", "XXX", "<procedure>", "as appropriate",
              "etc.", "lorem ipsum"]
    def check(p):
        text = p.read_text(encoding="utf-8").lower()
        hits = [b for b in banned if b.lower() in text]
        assert not hits, f"{p.name}: {hits}"
    _all(check)


def test_procedures_do_not_inline_gate_commands():
    """Commands are data in style/gate_commands.json. A procedure that inlines
    one creates a second copy with no checker, which is exactly the drift that
    moving them out of the old skill file was meant to end."""
    if not GATE_COMMANDS.is_file():
        return
    cmds = json.loads(GATE_COMMANDS.read_text())
    heads = {spec["cmd"].split()[0]
             for lang in cmds["languages"].values() for spec in lang.values()}
    heads -= {"test", "bash"}  # shell builtins, not toolchain names
    def check(p):
        text = p.read_text(encoding="utf-8")
        hits = [h for h in heads if re.search(rf"\b{re.escape(h)}\b", text)]
        assert not hits, f"{p.name}: inlines commands {sorted(hits)}"
    _all(check)


# ------------------------------------------------------------ gate commands

def test_gate_commands_cover_every_language_and_gate():
    if not GATE_COMMANDS.is_file():
        raise AssertionError(f"{GATE_COMMANDS} missing")
    d = json.loads(GATE_COMMANDS.read_text())
    order = d["gate_order"]
    assert len(order) == 6
    for lang, gates in d["languages"].items():
        assert list(gates) == order, f"{lang}: gates are {list(gates)}"
        for gate, spec in gates.items():
            assert spec["cmd"].strip(), f"{lang}/{gate}: empty command"
            assert spec["expect"] == 0, f"{lang}/{gate}: expect is not 0"


def test_gate_commands_record_their_verification_state():
    """Inherited invocations are unverified. Carrying the field means the gap is
    visible; dropping it would let an unrun command pass as trustworthy."""
    d = json.loads(GATE_COMMANDS.read_text())
    for lang, gates in d["languages"].items():
        for gate, spec in gates.items():
            assert "verified_on" in spec, f"{lang}/{gate}: no verified_on"


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
