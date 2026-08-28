"""
psyki.retinue — agent code indexed by toolset signature.

Because a task IS its toolset (I8), the second task with the same toolset is a
LOOKUP, not a generation. Over time AgentAgent writes less and retrieves more.

Two safety properties, both mandatory:

  hash-pinned — a contract cannot silently receive mutated code
  tool-versioned — a tool changing under a cached agent is a nasty silent
                   failure, so the signature includes tool versions

The retinue lives on disk indexed by signature. It never enters context.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

NEW = "NEW"


def toolset_signature(tools: dict[str, str]) -> str:
    """tools: {tool_name: version}. Order-independent, version-sensitive.

    Changing a tool version yields a different signature, so the old agent is
    simply not found rather than being wrongly reused. (§10.3)
    """
    h = hashlib.blake2b(digest_size=16)
    for name in sorted(tools):
        h.update(name.encode("utf-8"))
        h.update(b"\x00")
        h.update(tools[name].encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


@dataclass(frozen=True)
class AgentRef:
    signature: str
    code_hash: str
    path: str
    harness_path: str = ""      # cached test harness (§8)

    @property
    def pin(self) -> str:
        return f"{self.signature}:{self.code_hash}"


class PinMismatch(Exception):
    """Retrieved code does not match its pin. Fail closed."""


class Retinue:
    def __init__(self, root: str | Path) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)
        self._index: dict[str, AgentRef] = {}

    # -- lookup ----------------------------------------------------------

    def lookup(self, signature: str) -> Optional[AgentRef]:
        return self._index.get(signature)

    def resolve(self, signature: str) -> str:
        """Contract's agent_ref field: a pin, or NEW."""
        ref = self.lookup(signature)
        return ref.pin if ref else NEW

    # -- store -----------------------------------------------------------

    def enroll(self, signature: str, code: bytes,
               harness: bytes = b"") -> AgentRef:
        code_hash = hashlib.blake2b(code, digest_size=32).hexdigest()
        path = self._root / f"{signature}.py"
        path.write_bytes(code)

        harness_path = ""
        if harness:
            hp = self._root / f"{signature}.test.py"
            hp.write_bytes(harness)
            harness_path = str(hp)

        ref = AgentRef(signature, code_hash, str(path), harness_path)
        self._index[signature] = ref
        return ref

    # -- retrieve --------------------------------------------------------

    def checkout(self, pin: str) -> bytes:
        """Verify before handing code to a contract. Fail closed on drift."""
        signature, _, code_hash = pin.partition(":")
        ref = self._index.get(signature)
        if ref is None or ref.code_hash != code_hash:
            raise PinMismatch(f"no agent matching pin {pin}")
        code = Path(ref.path).read_bytes()
        actual = hashlib.blake2b(code, digest_size=32).hexdigest()
        if actual != ref.code_hash:
            raise PinMismatch(
                f"code at {ref.path} mutated: expected {ref.code_hash}")
        return code
