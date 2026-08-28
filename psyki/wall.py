"""
psyki.wall — user intent, encrypted and append-only.

Readable by the user (front end) and PSY. Nothing else. (I1)

The Wall holds ONLY directives — what should be true. Present state lives in
State (§6a) and agent reports live in the Log (§7). The Wall contributes
exactly one field to State: its revision number.

CIPHER NOTE
-----------
PSYKI v0 used a blake2b keystream XOR. That is a known defect, and it becomes
urgent the moment the Wall has a second writer, which the debrief path adds.

`Aead` below is the seam. Supply an XChaCha20-Poly1305 implementation
(PyNaCl or `cryptography`) at boot. `DevCipher` is UNAUTHENTICATED and refuses
to load unless explicitly opted into — it exists so the rest of the system is
testable, not so the Wall can ship without a real cipher.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import asdict
from typing import Iterator, Protocol

from .types import Directive, Urgency, Scope, Verb


class Aead(Protocol):
    """Authenticated encryption. Nonce management is the impl's problem."""

    def seal(self, plaintext: bytes, aad: bytes) -> bytes: ...
    def open(self, ciphertext: bytes, aad: bytes) -> bytes: ...


class InsecureCipherError(Exception):
    pass


class DevCipher:
    """NOT ENCRYPTION. Test double only."""

    def __init__(self, i_understand_this_is_insecure: bool = False) -> None:
        if not i_understand_this_is_insecure:
            raise InsecureCipherError(
                "DevCipher provides no confidentiality or integrity. "
                "Pass i_understand_this_is_insecure=True for tests, or supply "
                "a real XChaCha20-Poly1305 Aead for anything else."
            )

    def seal(self, plaintext: bytes, aad: bytes) -> bytes:
        return plaintext

    def open(self, ciphertext: bytes, aad: bytes) -> bytes:
        return ciphertext


class WallEntry:
    __slots__ = ("index", "prev_hash", "entry_hash", "blob")

    def __init__(self, index: int, prev_hash: str,
                 entry_hash: str, blob: bytes) -> None:
        self.index = index
        self.prev_hash = prev_hash
        self.entry_hash = entry_hash
        self.blob = blob


class Wall:
    """Append-only, hash-chained. Tampering with any entry breaks the chain."""

    GENESIS = "0" * 64

    def __init__(self, cipher: Aead) -> None:
        self._cipher = cipher
        self._entries: list[WallEntry] = []

    # -- write -----------------------------------------------------------

    def append(self, directive: Directive) -> int:
        """Only TasteTester-admitted directives reach here. (I6) The Wall does
        not validate — validation is a separate component so that the user's
        own boundary keeps an independent check."""
        prev = self._entries[-1].entry_hash if self._entries else self.GENESIS
        index = len(self._entries)

        plaintext = json.dumps(
            asdict(directive), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        aad = f"{index}:{prev}".encode("ascii")
        blob = self._cipher.seal(plaintext, aad)

        h = hashlib.blake2b(digest_size=32)
        h.update(prev.encode("ascii"))
        h.update(b"\x00")
        h.update(blob)
        entry_hash = h.hexdigest()

        self._entries.append(WallEntry(index, prev, entry_hash, blob))
        return self.rev

    # -- read ------------------------------------------------------------

    @property
    def rev(self) -> int:
        """The ONLY thing the Wall contributes to State. (§6a)"""
        return len(self._entries)

    @property
    def head(self) -> str:
        return self._entries[-1].entry_hash if self._entries else self.GENESIS

    def read(self) -> Iterator[Directive]:
        """PSY and the front end only."""
        for e in self._entries:
            aad = f"{e.index}:{e.prev_hash}".encode("ascii")
            body = json.loads(self._cipher.open(e.blob, aad))
            yield Directive(
                directive_id=body["directive_id"],
                verb=Verb(body["verb"]),
                scope=Scope(body["scope"]),
                urgency=Urgency(body["urgency"]),
                targets=tuple(body["targets"]),
                constraints=tuple(body["constraints"]),
                origin=body["origin"],
            )

    def verify_chain(self) -> bool:
        prev = self.GENESIS
        for e in self._entries:
            h = hashlib.blake2b(digest_size=32)
            h.update(prev.encode("ascii"))
            h.update(b"\x00")
            h.update(e.blob)
            if not hmac.compare_digest(h.hexdigest(), e.entry_hash):
                return False
            prev = e.entry_hash
        return True
