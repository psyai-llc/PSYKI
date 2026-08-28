# PSYKI

A self-governing, meta-agentic MCP server.

Three reasoning components. Everything else is deterministic code.

**Canon is [`docs/PSYKI_CORE.md`](docs/PSYKI_CORE.md).** Read it first — this
file is an orientation, not a specification. Where the two disagree, canon wins.

Rules for agents working on this repository: [`AGENTS.md`](AGENTS.md).

## Shape

| Component | Kind | Role |
|---|---|---|
| Emissary | model | Sole membrane. NL↔enum, both directions. |
| PSY | model | Temporal planner. Wall + present + history → target → objectives → tasks. |
| AgentAgent | model | Agent design, code authoring, test authoring. TaskMaster is its subagent. |
| KI | code | Certifying authority. Admits, certifies, revokes. Never reads text. |
| TasteTester | code | Schema + security validation at the Wall write path. |
| State | code | Bounded projection of all server data. Server core is sole writer. |
| Wall | code | Encrypted, user-authored, append-only. |
| Log | code | Server events + contract records. Bounded depth. |
| Retinue | code | Agent code indexed by toolset signature. Hash-pinned. |
| ProcOps | code | Read-only charter. Hash-verified on every read. |

Trust hierarchy: `ProcOps ≻ Wall ≻ Log`. A directive contradicting ProcOps is
voided, not negotiated.

## Layout

```
docs/PSYKI_CORE.md   canon
docs/notes/          design inputs — context, explicitly not canon
docs/v0/             superseded v0 sketch, archived
psyki/               runtime code (the only place Python lives, besides tests/)
tests/               invariant + structural gates
roles/               model-facing role specifications; never executable code
skills/              shared skill pool
style/               5-language style engine
tools/               tool manifest — partitions the task-type space
config/              model, MCP, and gate configuration
corpus/              read-only reference material
```

## Run

```bash
python -c "import psyki"      # package imports
python tests/test_invariants.py   # 27 invariant checks, no dependencies
python -m pytest tests/ -v        # full suite (needs pytest)
```

`tests/test_invariants.py` is the architecture's acceptance oracle: it encodes
the invariants from canon §2. `tests/test_repo_structure.py` is the structural
oracle for tree shape. Neither may be edited to make a suite green.

## Status

Ground-clearing passes are complete: the tree is reconciled and the invariant
suite is green. The system does not yet run end to end — PSY, the Emissary, the
server core's MCP surface, and the LLAW tier are unimplemented. See canon §10
for open questions.
