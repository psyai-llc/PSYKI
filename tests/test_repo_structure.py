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

# Shell- and Windows-hostile characters. Spaces, colons, parens and ampersands
# break pipelines and checkouts; case does not. Uppercase is handled separately
# by the case-collision rule below.
PORTABLE = re.compile(r"^[A-Za-z0-9._/-]+$")


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
    """No shell- or Windows-hostile characters in any tracked path."""
    offenders = [p for p in FILES if not PORTABLE.match(str(p))]
    assert not offenders, (
        "Paths must match ^[A-Za-z0-9._/-]+$ (no spaces, colons, parens, ampersands): "
        f"{_rel(offenders)}"
    )


def test_paths_survive_lowercasing():
    """Uppercase is allowed only where lowercasing collides with nothing.

    The real portability hazard is a case-insensitive filesystem (macOS,
    Windows), where two paths differing only in case are the same path and one
    silently overwrites the other. Banning uppercase outright was too strong —
    it forbade README.md and INDEX.md, which this same file requires to exist.

    The rule that actually protects the property: lowercase the whole tree and
    nothing may be lost.
    """
    lowered = Counter(str(p).lower() for p in FILES)
    collisions = sorted(name for name, count in lowered.items() if count > 1)
    assert not collisions, (
        "Paths that collide when lowercased — on a case-insensitive filesystem "
        f"these overwrite each other: {collisions}"
    )


def test_every_file_has_a_suffix():
    """Extensionless content files hide what they are.

    Two exemptions, both conventions rather than accidents: LICENSE, and
    dotfiles, where the leading dot is itself the type signal. The original
    rule caught `agentagent` and `The Phi Model guide` — real offenders — but
    also banned `.gitignore`, which every Python repo needs.
    """
    offenders = [
        p for p in FILES
        if not p.suffix and p.name != "LICENSE" and not p.name.startswith(".")
    ]
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
