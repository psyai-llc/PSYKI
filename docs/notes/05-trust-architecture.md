# Note 05 — Trust architecture: keys, signing, provisioning, authority

**Not canon.** Design input, per `docs/notes/readme.md`.

**Status: OPEN THROUGHOUT. Nothing here is scheduled for implementation.**
This document exists so the reasoning survives the gap between now and when it
is built. Every section describes a decided *shape* with undecided *details*.
Section 12 collects everything still open.

**Sequencing position.** All of this sits **after R1.3** — the spine has not yet
run end to end even with null components. Building a security architecture on
top of a loop that has never executed would mean debugging both at once, which
is the failure R1.3 exists to prevent. This is an end goal, not a next step.

**Relationship to note 06.** Note 06 covers the internal system: the loop, the
components, the invariants, what is built. This document covers everything that
crosses the boundary to the outside world — keys, the external authority, time,
and the ceremonies that bind them. §11 is the seam between the two.

**Prior art in-tree:** note 02 (cryptographic binding — the three-tier key
hierarchy, `binding_strength`, `projection_hash`), note 04 (successor key POST
validation — the only part of this architecture specified to implementation
grade).

---

## 1. What this architecture is for

PSYKI's charter tier (LLAW) is unauthorable by the running server. That property
is only meaningful if there is something outside the server that can author it,
and if the identity of that something is verifiable. L1 names it: **PSYAI is the
only external authority.**

Everything in this document follows from making that name mechanically real:

- Who the authority *is*, in a form a machine can check (a key, not a string).
- How the authority proves it is still there (liveness).
- What happens when it stops (succession).
- How the deployment moves to new hardware or new ownership (migration).
- How a deployment operates when it cannot reach any of this (offline).

The design goal underneath all of it: **the system should survive the authority's
absence without becoming a system anyone can capture.** Those pull against each
other, and most of the complexity here is the seam between them.

**Second design goal, equally binding:** none of this may make the ordinary case
difficult. A casual operator running a local MCP server should never encounter
most of this. The mechanisms exist for deployments that need them and stay
invisible otherwise.

---

## 2. The trust stack

```
   PSYAI root key                       external authority (L1)
        │  signs
        ├── successor delegation        pre-signed, escrowed, attenuable
        ├── migration grant             names EK_old → EK_new
        ├── offline lease               EK-bound, TPM-clock-expiring
        ├── LLAW amendment record       requires shutdown to apply
        └── liveness responses          over server-issued nonces
        
   ─────────────────────────── deployment boundary ───────────────────────────

   TPM Endorsement Key (EK)             per-deployment identity, non-signing
        │  credential activation
        └── Attestation Key (AK)        signs on the deployment's behalf
             └── ephemeral leaf keys    per-contract, short-lived (note 02)

   platform config (boot-read)
        ├── root key pin                current authority
        ├── successor slot              default NONE (note 04)
        ├── slot epoch                  monotonic, TPM NV
        ├── registration record         authority identity + contacts
        └── offline lease               if present
```

**The EK does not sign.** In TPM 2.0 it is conventionally a restricted
decryption key; signing is done by an Attestation Key certified to the EK via
credential activation. Wherever this document says "the deployment signs," the
mechanism is the AK. Note 02's three-tier hierarchy already assumes this.

**Hash is not signature.** Every authority artifact here is a signature over a
message, never a digest that happens to include the authority's public key.
Public keys are non-secret; anyone who has seen one can recompute a hash over
it. This was identified as a blocking flaw in an earlier attestation design and
must not reappear.

---

## 3. Registration and bootstrap

At first boot the server has no authority. Registration establishes one and
records what is needed to reach it later.

**Recorded at registration:**
- The external authority's public key (the root key pin).
- Contact endpoints for liveness notifications.
- The successor slot — `NONE` by default.
- The initial slot epoch.

**FLAG-T1 — the bootstrap hole.** Nothing verifies that whoever runs the
installer is entitled to become the authority. Every guarantee downstream rests
on this single unverified moment. This is the standard trust-on-first-use
problem. Candidate resolutions: ship with a manufacturer/vendor key so
enrolment is signed; or require an online enrolment handshake at first boot; or
accept TOFU explicitly and document it. **Unresolved, and load-bearing.**

**Registration data is security-relevant and belongs in the pinned tier.**
Whoever can rewrite the contact address redirects every future alert to
themselves, and the real authority never hears anything. Same treatment as the
successor slot: set at registration, changeable only under a signed act from the
current authority, and every change notified to **both** the old and new
addresses — that last part is what catches a silent redirect.

---

## 4. Root key rotation

Two-phase commit, patterned on UEFI KEK update and TPM ownership transfer.

1. The successor slot is written to platform config. Default `NONE`; while
   `NONE` the root key cannot change.
2. The server boots. POST validates the successor (note 04 — five checks:
   algorithm allowlist, well-formedness, distinctness after canonicalization,
   proof of possession, epoch monotonicity).
3. Only after a clean boot with status `VALID` may promotion occur — and
   promotion still requires a **separate rotation record signed by the current
   root**. Eligibility and authorization are different things.

**Why the separation matters:** if promotion fired automatically once a boot
cleared with a successor present, whoever can write platform config would own
the deployment after one reboot. The slot says who *may* inherit; the signed
record says *do it now*.

Note 04 is the only part of this architecture written to implementation grade,
including acceptance tests. Its FLAG-S1 (EK binding: identity or confinement)
is **resolved by §5** — migration is permitted under a grant, so the binding is
identity.

---

## 5. Migration

Moving a deployment to new hardware, or to new ownership. Two ceremonies that
share a mechanism and have different safety nets.

### 5.1 The grant

A migration grant is a signed artifact naming **`EK_old` → `EK_new`
explicitly**. Naming the old EK is what makes it a transfer rather than a fork:
without it, an orderly migration where the old machine keeps running yields two
deployments both claiming the charter.

Two independent credentials are required: the **authority's signature** and the
**successor's signature** over the new EK. Neither alone suffices. This is what
stops migration from being something a deployment can do to itself.

### 5.2 Orderly migration

The typical case, and the commercially important one: the business is sold, or
hardware is being replaced on schedule. Old hardware is alive. The authority is
reachable and signs the grant directly.

Failure is clean: the grant does not verify, the old deployment remains
authoritative, nothing has changed.

### 5.3 Recovery migration

Old hardware is dead — which is usually *why* the migration is happening. There
is nothing to revert to; failure here means no valid deployment at all, not a
reversion. This path deserves its own ceremony and its own scrutiny.

**The liveness problem this creates:** if a grant always requires the
authority's live signature, migration is impossible precisely when the authority
is gone — the scenario succession exists for.

**Resolution: the authority pre-signs while alive.** An attenuable delegation,
escrowed, granting the power to endorse an EK. It does not name a future EK
(that hardware does not exist yet). Post-authority, recovery presents the
escrowed delegation plus a successor signature over the new EK. Still
two-of-two, still no unilateral migration, and it survives the loss because the
authority's act happened *before* it. Same reasoning as shutdown-to-amend: bind
the authority to its own prior deliberation rather than requiring its presence.

**FLAG-T2 — escrow.** Who holds the pre-signed delegation, whether it is
threshold-split, and what prevents the holder from becoming the single point of
failure the whole design was built to avoid. **Unresolved.**

**FLAG-T3 — EK provenance.** Verifying a new EK is genuine TPM hardware pulls in
the manufacturer's CA chain as a third trust root, outside your control, which
can expire or be revoked. Decide whether to require it, and what happens when it
is unavailable.

---

## 6. Liveness

### 6.1 The protocol

The server issues a **fresh nonce**; the authority returns a **signature over
that nonce**. That signature is the proof of life and the only thing that is.

- An unauthenticated response proves nothing — anyone on the path can produce
  one, which would let an attacker keep a dead authority looking alive
  indefinitely and block a legitimate succession forever.
- A signature over an *old* nonce is a recording, not a life sign.

**Response is life. Time does not dictate it — time only measures silence.**

### 6.2 The peer clock check

One check among several against any external connection, never the
authenticator. The correct time is public; a peer that agrees with your clock
has proven it owns a watch. What validates a peer is the signature.

| Skew | Result |
|---|---|
| < 5 minutes | `PEER_CLOCK_ANOMALY` flagged and logged; connection proceeds |
| ≥ 5 minutes | break |

Useful for two things: bounding how long a captured response stays replayable,
and surfacing a peer whose clock is drifting or being manipulated — a finding
the auditor can see across checks that no single check would reveal.

**A broken liveness check is not a failed one.** If a 6-minute skew breaks the
connection and that counts as a missed check, anyone who can add five minutes of
delay to your packets can run the succession countdown to completion by doing
nothing else. A break yields `LIVENESS_INCONCLUSIVE`: logged, escalated
out-of-band, countdown **held**. The countdown advances only on a check that
completed and produced no valid signature.

### 6.3 Time

Two different jobs, and conflating them is what makes clock attacks work:

- **Wall clock** — stamps records for humans and external compliance. Enters the
  system as **data at ingress**, never as an ambient call. KI still reads a value
  it was handed, so I3 holds and replay uses the recorded stamp.
- **Monotonic (TPM) clock** — measures elapsed time. Survives reboots, carries a
  reset counter, cannot be slewed by host access.

**The countdown runs on the monotonic clock, never the wall clock.** A boot-time
anchor bounds skew *at boot*; the countdown runs for weeks and the server will
not reboot during it, so an anchor alone proves nothing about the interval.

Anchoring: each liveness check is itself a time anchor, since it is a signed
statement. Between checks, an external signed source (Roughtime, RFC 3161) with
a **fresh nonce** — never a fetched or cached timestamp.

**Anchor failure does not refuse boot.** Refusing would make the deployment
depend on someone else's availability, the opposite of the persistence goal.
Instead: boot proceeds, time is marked `UNANCHORED`, and **the succession
countdown cannot advance while unanchored.** The countdown is the one thing that
must never run on unverified time.

---

## 7. The dead-man switch

### 7.1 State

A single integer, `missed_checks`, 0–5.

- **Reset to 0** on any valid signed response. Nothing else resets it.
- **Advances** on a check that completed and returned no valid signature.
- **Held** on `LIVENESS_INCONCLUSIVE`, while `UNANCHORED`, and while a valid
  offline lease is in force.

| Count | Meaning |
|---|---|
| 0 | healthy |
| 1 | first miss — notification, low alert |
| 2 | second miss — notification, raised |
| 3 | **firm-date notice** — names the exact date and remaining checks before death, and states plainly what happens then |
| 4 | authority considered dead; recovery ceremony opens |

### 7.2 Grace

An acknowledgement to a notification buys **+2 checks, once per countdown**.

It **pauses; it does not reset.** This is the important asymmetry: if a
notification response could reset the countdown, anyone with access to that
inbox could suspend succession indefinitely — and inbox compromise is the
cheapest attack available. Grace is consumed whether or not it saves the
situation; only a signed response clears it and returns the budget.

Capped at one use, hard. Two uses of +2 is +4, and an uncapped grace is an
unbounded stall via inbox access. **The invariant to test: no sequence of
acknowledgements without a signature ever prevents death.**

Worked example — an admin who first reads their mail at miss 3: one check
remaining, acknowledge for +2, now three remaining, hard date stated.

### 7.3 Notifications

The scenario this is built for is unremarkable: a company physically relocating
its servers for a week, forgetting to pre-warn the deployment. Not adversarial,
entirely normal, and a naive countdown reads it as death.

- Escalate rather than repeat — increasing urgency, not the same mail five
  times.
- Multiple channels. Email alone is a single point of failure, and in the
  relocation scenario mail routing may be part of what is broken.
- The firm-date notice must embed the countdown position: remaining checks,
  what grace would buy, the hard date. Not a generic warning. This is a
  formatting requirement on the implementation, not a suggestion.

**Known limit:** none of this survives an authority that is both gone *and*
whose contact channels are gone. That is what the successor slot is for.

### 7.4 Accepted risk

A sustained availability attack on the liveness channel manufactures a death.
Mitigations: multiple independent channels, a long window, out-of-band
notification on every miss, and succession that **requires the successor to act
and sign** — never firing silently on a timer. This is an accepted cost, written
down as one.

---

## 8. Offline operation

### 8.1 Why freeze is the default

An offline server that keeps operating **produces a fork**: it signs artifacts
under a charter it cannot verify is current, timestamped by a clock it cannot
verify, and those enter the ledger. On reconnect there are two divergent
histories and no principled way to reconcile them.

That argument also bounds the freeze — what must stop is anything that **writes
signed state**.

**Freeze semantics:** refuse new admissions; let in-flight contracts drain or
abort with a record; keep the log and the read surface alive. A total halt with
no observability makes the failure undiagnosable exactly when someone needs to
diagnose it.

**Transient loss is not offline mode.** A threshold of missed anchor attempts
must pass before freeze engages, with immediate resume on reconnect. Otherwise
the system halts every time a router reboots.

**Accepted risk:** freeze-by-default is a denial switch for anyone who can cut a
cable. Defensible because the alternative is ledger divergence — but it is the
cheapest attack against the system and is recorded as such.

### 8.2 The lease

A signed offline permit, which is a **lease, not a switch**.

- **EK-bound** — not portable to another deployment.
- **Expires on TPM clock ticks** — works offline precisely because the monotonic
  clock is internal.
- **Starts at issuance, not at going offline.** A permit issued in January and
  used in June gives an unexamined window since January. The intuitive reading
  is the wrong one; state it explicitly.
- Maximum term on the order of 30 days (**FLAG-T4** — exact value unset).
- Carries its expiry date visibly, so it is known from day one.

This makes long-term air-gapped operation a supported configuration rather than
a hole — a real requirement for secure projects, and a real market. It also
covers any deployment that is intermittently connected by design, for which
offline is the normal operating state rather than a fault.

### 8.3 Reconciliation

Renewal is not a rubber stamp. Going online to renew is a ceremony:

1. Anchor time against the external source.
2. Verify LLAW digest and ProcOps pin against what the authority currently holds.
3. Submit the offline ledger segment for anchoring.
4. Receive any charter updates.
5. **Issue the next lease — last, and contingent on 1–4 succeeding.**

If renewal came first, thirty days of unexamined operation would compound
indefinitely.

**Atomic.** If the connection drops mid-ceremony, either it completed and a new
lease exists, or nothing changed and the old lease runs to its original expiry.
No partial credit.

**Expiry with no renewal is hard, and stays hard.** There is no override; an
override would make the lease meaningless. What the operator gets is escalating
warnings on the TPM clock well before expiry and a visible expiry date. The
remedy for an expired lease is a trip to a network — a real operational cost,
and the thing being traded for.

**One clean consequence:** freeze-on-expiry is the same freeze as unpermitted
offline. One code path, one set of semantics. A permit does not change what
freeze means; it changes when it starts.

### 8.4 Interaction worth knowing

A deployment under a valid lease has its countdown held, so it cannot be
declared dead. Abandonment during offline mode is therefore invisible until the
lease expires. Not a defect — a property, recorded so it is known rather than
discovered.

---

## 9. LLAW amendment

Amending the charter requires the server **not to be running**. This is what
separates LLAW from ProcOps mechanically rather than by promise: `CharterDrift`
stops being a runtime detection and becomes a physical impossibility, and the
primary enforcement point moves to boot — compute the digest, compare to the
pin, refuse to start on mismatch. Fail closed.

Three costs, accepted deliberately:

1. **Clean drain.** In-flight contracts complete or are logged as aborted before
   halt, or amendment becomes a way to lose state quietly.
2. **No emergency runtime override, ever.** If a law is actively causing harm,
   the remedy is downtime. Any hot-patch path destroys the property entirely,
   and that path is exactly what will be proposed at 3am under pressure.
3. **Friction is the feature.** Amendment is expensive by construction so it
   cannot be casual, and the authority is bound by its own past deliberation.

**Restart must verify the new digest against a signed amendment record**, or the
ceremony launders arbitrary changes — "shutdown to amend" would otherwise double
as "shutdown to swap the binary."

**For the ProcOps hot path, which stays running:** capture the pin **per
contract at admission**. `admit()` already checks `procops_hash`; carrying that
hash in the contract means a contract is judged under the charter that admitted
it. Otherwise a mid-flight pin update means the gate chain that let something in
is not the one that judges it, and every ProcOps tune would need a full drain.

---

## 10. Default successor — product consideration

**Recorded as a product/legal decision, not an architectural one.**

The proposal: PSYKI ships with PSYAI as the default successor, so that an
abandoned customer deployment reverts to PSYAI under published terms.

**Assessment:** the mechanism is fine; the placement is not. MIT is a copyright
licence on code — it cannot transfer a deployment, its data, or its
infrastructure. When a company fails, its assets move under dissolution or
bankruptcy law, controlled by a trustee or creditors; a clause embedded in
software has no standing there, and a term never in a signed agreement is not a
contract. It is also self-defeating: MIT means the default can be forked out in
an afternoon.

Putting the terms in a signed purchase agreement fixes the legal problem — and
once they are there, the *code* default is redundant. What remains is the cost:
a vendor holding a root-of-trust position by default is what an enterprise
security review looks for, and it sits badly against the sovereignty argument
that motivates the whole architecture. If PSYKI refuses an external authority
over itself, a customer's deployment should name the customer's authority.

**Recommendation:** slot defaults to `NONE`. Setting it is part of onboarding.
Offer PSYAI-as-successor as a **disclosed, revocable, opt-in** service with
published terms — some customers will genuinely want a successor they do not
have to nominate. The ones who do not will notice that you asked.

Architecturally, abandonment costs nothing: the frozen charter means the
deployment keeps running correctly without anyone.

---

## 11. Seam with the internal system (note 06)

Where this architecture touches the loop:

| Touchpoint | Internal effect |
|---|---|
| `llaw_hash` in `StateSnapshot` and `Certificate` | R1.1 — KI refuses and revokes on `LAW_DRIFT`, checked **before** `procops_hash` |
| Boot-time POST | New `psyki/boot.py`; never in `ki.py` (I2, I3) |
| Crypto | New `psyki/keys.py`; all library-specific code isolated there |
| Time as stamped data at ingress | State gains a stamped field; KI stays pure |
| `SuccessorStatus`, `LivenessState`, `OfflineState` | Scalar enums in State — I4-clean, auditor-readable |
| Freeze | Expressed through KI admission, not a separate halt path |
| `binding_strength` (note 02) | R1.7 — asserted-only models barred from sensitive tiers |
| Per-contract ProcOps pin | Contract carries the hash that admitted it |

**None of these are R1 work.** They are listed so that R1 does not accidentally
foreclose them — chiefly by keeping time out of KI, keeping crypto out of the
core, and keeping every new State field scalar or enum.

---

## 12. Open flags

| # | Flag | Severity |
|---|---|---|
| **T1** | **Bootstrap / TOFU.** Nothing verifies that whoever runs the installer is entitled to become the authority. Every downstream guarantee rests on this unverified moment. | **Load-bearing** |
| **T2** | **Escrow** for the pre-signed successor delegation: who holds it, threshold-split or not, and what stops the holder becoming a single point of failure. | High |
| **T3** | **EK provenance** — whether to require the TPM manufacturer's CA chain, and behaviour when it is unavailable or revoked. | Medium |
| **T4** | **Parameters unset:** liveness check interval (a month is four checks only if checks are weekly); external time anchor source; notification channels beyond email; transient-loss threshold before freeze; maximum lease term. | Medium |
| **T5** | **Succession law text.** L2 was drafted for the governance audit and never finished; whether the next law is the audit law, a succession law, or both is undecided. Whichever lands first must handle the `len(llaw.LLAW) == 1` arity assertion — a spec change, not a fix (AGENTS.md §4). | Medium |
| **T6** | **Auditor / countdown parameter capture.** Check interval and miss ceiling are levers on succession timing. If they become ProcOps-tunable, the auditor could propose loosening constraints that govern succession. Both should be authority-only changes. | Medium |
| **S1** | Resolved by §5 — EK binding is **identity**, migration permitted under grant. | Closed |
| **S2** | Rotation record — shape given in §4; not specified to implementation grade. | Open |
| **S3** | PoP proves possession at signing time, not boot time. Unfixable at boot; mitigated procedurally. | Accepted |
| **S4** | `llaw_digest` excluded from the PoP challenge; belongs in the rotation record. | Decided |
| **S5** | `slot_epoch` needs a hardware monotonic counter (TPM NV, increment-only). Config-stored epochs are rollback-able. | Open, real dependency |
| **S6** | Ed25519 verification strictness varies by library; pin library and mode in `keys.py`. | Open |
