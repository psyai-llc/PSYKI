# Note 01 — One Wall, N producers

**Not canon.** Design input. Canon (`docs/PSYKI_CORE.md`) wins on conflict.

## Position

One Wall for all systems is architecturally correct. A single audited ingress is
the entire reason the Wall exists; duplicating it per subsystem yields N
boundaries with N different failure modes. **Keep it singular.**

## The consequence to design for now, while it is cheap

Today the Wall holds user drives and one human generates them slowly. Tie in
ambient sensors, a scanner, spectral streams, N subsystems — and it stops being
a channel and becomes **a queue with contention**: many producers at very
different rates writing to the one structure PSY reads as its context.

Three things follow.

1. **Ordering matters and is not defined.** Canon §10.2 already flags event fold
   ordering as open. Tolerable at one producer; at N it determines what PSY sees.

2. **Rate asymmetry becomes a denial channel.** A sensor emitting 1000/sec and a
   human emitting 1/hour share a bounded context. Without per-origin quotas the
   fast producer evicts the slow one — and the slow one is the human. This is not
   hypothetical; it is the default behaviour of any shared buffer.

3. **Per-origin reputation stops being optional.** TasteTester already carries the
   concept. With one Wall for everything, origin becomes the primary axis of
   trust, and every producer needs a lineage.

## The fix, if done before there are producers

Origin-tagged admission with per-origin bounded budgets, plus **a floor reserved
for human drives that no other producer can consume.** This directly protects
against the human channel being crowded out by volume.

## Touch points in the current tree

| Concern | Location |
|---|---|
| Origin field | `psyki/types.py::Directive.origin` — currently `USER \| DEBRIEF \| RETRIEVAL` |
| Origin validation | `psyki/tastetester.py::VALID_ORIGINS` |
| Wall append path | `psyki/wall.py::Wall.append` — no quota, no backpressure |
| Fold ordering | `psyki/core.py::ServerCore.fold` — one increment per batch, order within batch undefined |

## Out of scope

**The Spectral Neural Network lies beyond current scope.** It is tied to
long-term PSYAI (Psy-ai LLC, New Mexico) goals, not to this build. The
contention design above stands on its own — it is about many producers on one
bounded ingress, whatever those producers eventually are.

Recorded so the question is not re-opened by inference: no sensor, scanner, or
spectral producer is being built now, and the per-origin budget work below is
therefore **not yet warranted**. Build it when the second producer appears, not
before.
