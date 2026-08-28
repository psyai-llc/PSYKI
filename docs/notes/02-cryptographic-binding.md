# Note 02 — Cryptographic binding

**Not canon.** Design input. Canon (`docs/PSYKI_CORE.md`) wins on conflict.

## The blocking flaw

A hash is not a signature. `psyki/ki.py::mint_certificate_id` currently derives a
certificate id as `blake2b(task_id, state_rev, procops_hash)`. Every input is a
value presented to counterparties, so none of them is secret — anyone who has
seen them recomputes the same stamp and forges an action attributed to someone
else. Hashes also do not decode, so a stamp cannot carry a trace.

**Resolution: KI is the certification authority.** This is already canon — I9,
"certificates are issued and revoked by KI alone." The current hash is a
placeholder standing where a signature belongs. KI does not need a new role; it
needs to actually sign.

### Determinism is preserved — but only with the right primitive

I3 requires KI to be a pure total function: no RNG. This appears to forbid
signing, and does forbid **ECDSA**, whose per-signature random `k` is a fresh
secret each call.

**Ed25519 (RFC 8032) is deterministic by construction** — the nonce is derived
by hashing the private key with the message, so identical inputs yield a
byte-identical signature. KI can sign every certificate and still satisfy I3 and
`tests/test_invariants.py::test_ki_is_deterministic` unmodified.

This is load-bearing: the choice of signature scheme is not a preference here,
it is what decides whether KI can be a CA at all. RFC 6979 deterministic ECDSA
would also work; plain ECDSA must never be used.

## Open items

1. **Arguments are not bound.** A stamp proves who called a tool, never what
   they passed it. Valid identity plus mutated payload is currently undetectable.
   The signed envelope must cover the arguments, not just the caller.

2. **Replay.** A timestamp does not prevent replay, and a caller-supplied one is
   attacker-controlled. The server core should issue a nonce and sequence number.
   TPM clock plus reset count gives ordering that survives restart.

3. **TPM throughput.** Tens to hundreds of milliseconds per operation makes
   per-call TPM signing both a throughput ceiling and a DoS target. Use the TPM
   as a root that certifies short-lived ephemeral keys, and anchor batches by
   Merkle root rather than signing each call.

4. **Hosted models cannot be cryptographically bound.** Nothing proves returned
   tokens came from the model ID requested. Local weights can be bound; hosted
   API models can only be asserted. A `binding_strength` field on
   `Contract.model_binding` should bar asserted-only models from sensitive
   capability tiers, rather than papering over the gap.

5. **Bind each stamp to the projection hash PSYKI acted on.** Because context is
   state in this design, this makes every trace answer *"what did the system
   believe when it decided this."* `StateSnapshot` carries `state_rev` but no
   content hash; adding one gives the efficiency-audit cycle exactly the anchor
   it needs. Conventional PKI does not provide this.

## FLAG-A — governance, not engineering

**Who operates the external authority, and what does it verify before issuing a
model certificate?** The entire zero-trust claim rests on this, and it is not a
technical decision. Unresolved.

## Touch points in the current tree

| Concern | Location |
|---|---|
| Certificate minting | `psyki/ki.py::mint_certificate_id` |
| Certificate fields | `psyki/types.py::Certificate` |
| Model binding strength | `psyki/types.py::Contract.model_binding` |
| Capability tiers | `psyki/types.py::CapabilityFloor` |
| Projection hash anchor | `psyki/types.py::StateSnapshot` |
| Wall integrity | `psyki/wall.py` — canon §9 already requires XChaCha20-Poly1305 |
