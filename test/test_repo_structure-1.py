"""Structural invariants for the PSYKI repository.

This is the acceptance oracle for R0.3 (tree reconciliation). Every test here
MUST fail against the pre-reconciliation tree and pass after. Run it before
starting work to confirm it fails; a structural test that already passes is
testing nothing.

No agent may edit this file to make it pass. The test is the specification.
"""

from __future__ import annotations

import re
import subprocess
from collections import Counter
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def tracked_files() -> list[Path]:
    """Git-tracked paths only. Untracked scratch and ignored files are not our problem."""
    out = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [Path(p) for p in out.split("\0") if p]


FILES = tracked_files()

PROSE_SUFFIXES = {".md", ".pdf", ".rst", ".txt", ".docx"}
PORTABLE = re.compile(r"^[a-z0-9._/-]+$")

# Paths exempt from the lowercase-portable rule. Keep this list short and
# justified; every entry is a place drift can hide.
PORTABLE_EXEMPT = {
    "AGENTS.md",
    "LICENSE",
    "README.md",
    "docs/PSYKI_CORE.md",
    "docs/INVARIANTS.md",
    "docs/TREE.md",
}


def _rel(paths: list[Path]) -> list[str]:
    return sorted(str(p) for p in paths)


# --------------------------------------------------------------------------
# Code / prose separation. I4 is unenforceable while prompts live in the
# runtime package, so this is the structural precondition for it.
# --------------------------------------------------------------------------

def test_no_python_outside_package():
    """All runtime code lives in psyki/. Tests and examples are the only exceptions."""
    allowed_roots = ("psyki/", "tests/", "examples/")
    offenders = [
        p for p in FILES
        if p.suffix == ".py" and not str(p).startswith(allowed_roots)
    ]
    assert not offenders, f"Python outside psyki/, tests/, examples/: {_rel(offenders)}"


def test_no_prose_in_package():
    """No prompts, specs, or documents inside the runtime package."""
    offenders = [
        p for p in FILES
        if str(p).startswith("psyki/") and p.suffix.lower() in PROSE_SUFFIXES
    ]
    assert not offenders, f"Prose inside psyki/: {_rel(offenders)}"


def test_no_code_in_roles():
    """roles/ holds model-facing specification only. Never executable code."""
    offenders = [
        p for p in FILES
        if str(p).startswith("roles/") and p.suffix in {".py", ".sh", ".bash"}
    ]
    assert not offenders, f"Executable code inside roles/: {_rel(offenders)}"


# --------------------------------------------------------------------------
# Canon singularity. Two representations of the charter is two charters.
# --------------------------------------------------------------------------

def test_canon_is_singular():
    canon = [p for p in FILES if p.stem.upper() == "PSYKI_CORE"]
    assert len(canon) == 1, f"Expected exactly one PSYKI_CORE.*, found: {_rel(canon)}"
    assert str(canon[0]) == "docs/PSYKI_CORE.md", (
        f"Canon must be docs/PSYKI_CORE.md, found {canon[0]}"
    )


def test_v0_is_archived_and_bannered():
    """The superseded v0 design must exist, must be in docs/v0/, and must say so."""
    v0 = REPO / "docs" / "v0" / "README-v0.md"
    assert v0.exists(), "docs/v0/README-v0.md missing — v0 must be archived, not deleted"
    head = v0.read_text(encoding="utf-8")[:600].upper()
    assert "SUPERSEDED" in head, "v0 archive must carry a SUPERSEDED banner in its first lines"


# --------------------------------------------------------------------------
# Duplicates. ki.py existed twice; that must never recur silently.
# --------------------------------------------------------------------------

def test_no_duplicate_basenames():
    ignore = {"__init__.py", "readme.md", "README.md", "INDEX.md", "index.md"}
    names = [p.name for p in FILES if p.name not in ignore]
    dupes = {n: c for n, c in Counter(names).items() if c > 1}
    assert not dupes, f"Duplicate filenames across the tree: {dupes}"


# --------------------------------------------------------------------------
# Portability. Spaces and colons break Windows checkouts and shell pipelines.
# --------------------------------------------------------------------------

def test_paths_are_portable():
    offenders = [
        p for p in FILES
        if str(p) not in PORTABLE_EXEMPT and not PORTABLE.match(str(p))
    ]
    assert not offenders, (
        "Paths must match ^[a-z0-9._/-]+$ (no spaces, colons, parens, capitals): "
        f"{_rel(offenders)}"
    )


def test_every_file_has_a_suffix():
    offenders = [p for p in FILES if not p.suffix and p.name not in {"LICENSE"}]
    assert not offenders, f"Extensionless files: {_rel(offenders)}"


# --------------------------------------------------------------------------
# Things CORE §9 explicitly says not to inherit.
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "pattern,reason",
    [
        (r"\.zip$", "PSYKI_CORE.md §9: do not inherit agentagent2-complete.zip"),
        (r"\(\d+\)", "PSYKI_CORE.md §9: do not inherit duplicate (1) files"),
        (r"verify_report.*\.json$", "PSYKI_CORE.md §9: do not inherit verify_report*.json"),
    ],
)
def test_core_section_9_exclusions(pattern, reason):
    rx = re.compile(pattern)
    offenders = [p for p in FILES if rx.search(str(p))]
    assert not offenders, f"{reason} — found: {_rel(offenders)}"


# --------------------------------------------------------------------------
# The package must actually import.
# --------------------------------------------------------------------------

def test_package_imports():
    r = subprocess.run(
        ["python", "-c", "import psyki"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, f"`import psyki` failed:\n{r.stderr}"


def test_corpus_has_an_index():
    assert (REPO / "corpus" / "INDEX.md").exists(), (
        "corpus/INDEX.md missing — a corpus without an index is a pile"
    )
