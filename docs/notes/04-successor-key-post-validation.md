# Note 04 — Successor key: POST validation

**Not canon.** Design input, per `docs/notes/readme.md`. Where this and
`docs/PSYKI_CORE.md` disagree, canon wins. Items marked **AMEND CANON** or
**FLAG** are proposals and open questions, not statements of fact.

**Scope.** This specifies exactly one thing: what the server checks about the
successor key slot at boot, and what it does with the answer. It does **not**
specify the rotation ceremony, the escrow, or who declares a successor. Those
are separate and larger; see FLAG-S2.

---

## 1. The property being bought

The successor slot is platform configuration, read at boot, defaulting to
`NONE`. While it is `NONE` the root key cannot change. Promotion requires a
clean boot with the slot populated, which means a bad successor is discovered
while the current root is still valid and still able to correct it.

That guarantee is worth nothing if "clean boot" only means the process started.
A slot containing a typo, a truncated key, or a public key whose private half
does not exist would clear a presence check and then brick amendment forever at
the moment of promotion.

**POST must therefore prove the successor key is usable, not merely present.**

---

## 2. The five checks

In order. Any failure short-circuits to `INVALID` (§4); none of them are fatal
to boot.

| # | Check | Failure mode it closes |
|---|---|---|
| 1 | **Algorithm is in the frozen allowlist** | An unlisted or weak algorithm smuggled in through config |
| 2 | **Key parses and is well-formed for that algorithm** | Truncation, corruption, wrong encoding, identity/small-order points |
| 3 | **Key is distinct from the current root, after canonicalization** | Promotion to the incumbent — a no-op rotation that looks successful |
| 4 | **Proof of possession verifies** | A public key whose private half does not exist or was mistyped |
| 5 | **Slot epoch is strictly greater than the recorded epoch** | Replay of a previously retired successor |

### 2.1 Algorithm allowlist

```python
SUCCESSOR_ALGS: Final[tuple[str, ...]] = ("ed25519",)
```

Lives in `psyki/llaw.py` and is **folded into the LLAW digest**. This is the
fix for the hole where a law's meaning depends on data outside the thing that is
pinned: if the allowlist lived in ProcOps or config, widening it would change
what the law permits without ever tripping `CharterDrift`.

**Consequence:** `_derive_hash()` must be extended to cover the allowlist, which
changes `PINNED_HASH`. See §7.

Ed25519 only, to start. One algorithm means one verification path, and a
verification path that is never exercised is a verification path that is wrong.

### 2.2 Well-formedness

For Ed25519: exactly 32 bytes after canonicalization; not the all-zero key; not
a known small-order point. Reject non-canonical signature encodings and `S ≥ L`
at verification time — Ed25519 implementations differ on strictness, and this is
one of the few places where the divergence is exploitable.

### 2.3 Distinctness

Compare **canonical raw public key bytes**, not the config string. A DER-wrapped
and a raw encoding of the same key are the same key, and a byte comparison on the
config value would call them distinct. Canonicalize first, then compare.

### 2.4 Proof of possession — the load-bearing check

The successor holder is not present at boot, so the signature must be
pre-computed when the slot is written and verified deterministically at every
boot thereafter. That rules out a fresh random challenge and requires a
*derived* one.

```
POP_DOMAIN = b"psyki.successor.pop.v1"

challenge = blake2b-256(
    POP_DOMAIN        || 0x00 ||
    ek_pub            || 0x00 ||    # this deployment
    root_pub          || 0x00 ||    # this transition
    successor_alg     || 0x00 ||    # algorithm binding
    successor_pub     || 0x00 ||    # the subject
    slot_epoch                      # u64 big-endian
)
```

Verified as `Verify(successor_pub, challenge, slot_signature)`.

Every field is load-bearing:

- **domain separator** — the signature cannot be a signature harvested from
  another protocol that happens to sign 32-byte digests.
- **`ek_pub`** — binds the PoP to this deployment. A successor slot lifted from
  another PSYKI instance does not verify here.
- **`root_pub`** — binds it to this specific transition. A PoP produced under a
  previous root does not carry forward across a rotation.
- **`successor_alg`** — closes algorithm confusion: the same 32 bytes
  interpreted under a different scheme is a different message.
- **`slot_epoch`** — closes replay of a retired successor (§2.5).

**Not included: `llaw_digest`.** Binding the PoP to the charter would force the
successor holder to re-sign on every LLAW amendment, and it buys little —
the PoP proves *possession*, not *authorization*. Authorization belongs in the
rotation record, which is where the charter binding should go instead.
**FLAG-S4** if you disagree; it is a one-line change and much cheaper now.

### 2.5 Slot epoch, and where it must live

`slot_epoch` is a counter incremented on every slot write. It is what stops an
attacker with config write access from reinstalling a successor that was
previously retired.

**This only works if the epoch cannot decrease.** If it is stored in ordinary
platform config alongside the slot, whoever can write the slot can also roll the
epoch back, and the anti-replay evaporates. It needs a monotonic counter with
hardware backing — a TPM NV index with an increment-only attribute is the
natural home, and the deployment already has a TPM by virtue of the EK.

This is a real dependency, not a detail. **FLAG-S5.**

---

## 3. Where this code lives

- `psyki/boot.py` — **new.** POST sequence. Not `ki.py`: KI is a pure total
  function over `(State, Plan, Event)` (I2, I3) and has no business reading
  platform config or calling a crypto library. The I3 CI grep would also fire.
- `psyki/keys.py` — **new.** Thin wrapper over the crypto library. Parse,
  canonicalize, verify. Everything library-specific stays here, so swapping
  implementations is one file. Same reasoning as the adapters rule.
- `psyki/llaw.py` — gains `SUCCESSOR_ALGS` and the extended `_derive_hash`.

No new law is required for this note. §2 is a mechanism the succession law will
eventually reference; writing the mechanism first means the law can name a
predicate that actually exists.

---

## 4. Failure policy

| Slot state | `SuccessorStatus` | Boot | Rotation |
|---|---|---|---|
| absent | `NONE` | proceeds | barred |
| present, all five checks pass | `VALID` | proceeds | permitted |
| present, any check fails | `INVALID` | **proceeds** | barred |

**Boot does not refuse on an invalid successor.** This is deliberate and it is
the opposite of the LLAW digest check, which *does* refuse. The difference:
a LLAW mismatch means the charter under which the server would run is not the
charter that was reviewed — running is the harm. An unusable successor slot means
only that a future rotation cannot proceed. Refusing to boot on it would hand
anyone with config write access a way to take the whole deployment down.

The cost is that a corrupted slot is a denial of *rotation*, silently, unless
someone looks. So:

- `SuccessorStatus` is a State field — scalar enum, I4-clean.
- `INVALID` is logged at boot with the failing check.
- The governance auditor reads it. **`NONE` is a healthy steady state and must
  be reported as a standing condition, not a fault** — otherwise every audit
  flags it and the flag becomes noise. `INVALID` is a finding.

---

## 5. Acceptance tests — write these first

Per AGENTS.md §4: write, run, **confirm each fails**, then implement. A test
that passes before the change is a defect in the task.

```
test_absent_slot_yields_status_none
    no slot configured → status NONE, boot returns normally

test_malformed_key_is_invalid_not_fatal
    31-byte key → status INVALID, boot returns normally, reason recorded

test_all_zero_key_refused
test_small_order_point_refused

test_successor_equal_to_root_refused
    same key, raw encoding → INVALID

test_successor_equal_to_root_refused_across_encodings
    same key, DER vs raw → INVALID
    (this is the one that fails if canonicalization is skipped)

test_unlisted_algorithm_refused
    alg not in SUCCESSOR_ALGS → INVALID

test_pop_verifies_against_derived_challenge
    sign the derived challenge with the successor private half → VALID

test_pop_from_another_deployment_refused
    valid signature, different ek_pub in the challenge → INVALID

test_pop_bound_to_previous_root_refused
    valid signature computed under the prior root_pub → INVALID

test_pop_over_a_different_key_refused
    signature valid, but over a challenge naming a different successor_pub

test_replayed_epoch_refused
    slot_epoch ≤ recorded epoch → INVALID

test_non_canonical_signature_refused
    S ≥ L → INVALID

test_invalid_successor_bars_rotation
    status INVALID → rotation entry point refuses

test_valid_successor_does_not_itself_rotate
    status VALID → root key is unchanged after boot
    (promotion requires the rotation record — §6 / FLAG-S2)
```

The last two are the ones that catch a wrong mental model rather than a wrong
implementation, and they are the two most likely to be skipped.

---

## 6. What this spec deliberately does not do

**It does not promote anything.** A clean boot with `VALID` makes the successor
*eligible*. Promotion requires a separate signed act by the **current** root — a
rotation record. Without that separation, whoever can write platform config owns
the deployment after one reboot, which inverts the entire property.

The rotation record is the natural place for `llaw_digest` (§2.4), for the
timestamp, and for the durable artifact that proves the transfer was intended.
It is out of scope here and is the next thing to write.

---

## 7. Mechanical gotchas for whoever implements

1. **`PINNED_HASH` changes.** Folding `SUCCESSOR_ALGS` into `_derive_hash()`
   makes `test_llaw_verifies_against_its_pin` fail until the pin is updated.
   AGENTS.md §4 forbids editing an acceptance test to match an implementation,
   and an agent hitting this will correctly open a `BLOCKED:` PR. **The task
   brief must state explicitly that recomputing and updating `PINNED_HASH` is
   part of this change, not a workaround.** Same for
   `test_llaw_hash_is_deterministic` if the derivation is touched carelessly.

2. `len(llaw.LLAW)` is unchanged — no new law here — so
   `test_llaw_cannot_be_extended_at_runtime` should stay green. If it goes red,
   something added a law that this note did not ask for.

3. The I3 determinism job greps `psyki/ki.py` for nondeterminism imports. Keep
   every crypto and config import in `boot.py` and `keys.py`.

4. `blake2b` is already the digest in `llaw.py`. Use it here too rather than
   introducing a second hash function; one primitive, one failure surface.

---

## 8. Open flags

| # | Flag |
|---|---|
| **FLAG-S1** | **EK binding: identity or confinement?** Strict pairing means hardware death is unrecoverable — no TPM, no valid root, permanently. Loose pairing means the charter can migrate under a signed act. Both are defensible; they are different systems. Given the persistence goal, choose deliberately and now. |
| **FLAG-S2** | The rotation record. This spec is inert without it. Needs its own note. |
| **FLAG-S3** | PoP proves possession **at signing time, not at boot time**. The private half could have been destroyed the day after the slot was written and every boot would still report `VALID`. Unfixable at boot by construction. Mitigation is procedural: a periodic re-attestation ceremony, and the auditor reporting slot age. |
| **FLAG-S4** | Whether `llaw_digest` belongs in the PoP challenge (§2.4). Recommendation: no — put it in the rotation record. |
| **FLAG-S5** | Monotonic counter for `slot_epoch` (§2.5). Config-stored epochs are rollback-able and defeat the replay check. TPM NV index is the natural answer; confirm the deployment target supports it. |
| **FLAG-S6** | Ed25519 verification strictness varies by library (RFC 8032 vs. FIPS 186-5 divergence on cofactored verification). Pin the library and the strictness mode in `keys.py` and test the boundary cases rather than trusting a default. |
