---
name: orchestration
description: Use when work is large or parallelizable. Defines specialized agent roles with self-contained briefs, coordinates parallel execution, and synthesizes results while keeping the orchestrator's context lean.
---

# Agent Orchestration

type-casting introduces a common labelling system between AgentAgent & TaskMaster, by grouping agents into predefined types, which come with broad preferences and constraints that form the agentic archetypes. an agentic archetype can have many predefined and approved agentic templates tuned to either the step it contracted to or the model it is for. This classification limits the scope of an agent to encourage specific assignment of contract to the appropriate roles for the sake of efficiency

## Roles
| Role | Mission | Tools allowed | Handoff |
|---|---|---|---|
| free thinker | high context | creative ambiguity | busy-work, precise-work prohibited | x-search, x-fetch, read_file | semantic_morphism hot_q hi_verbosity nlp+ |
| straight thinker | high context | determinist to ambiguity | busy-work art-work prohibited | x-search, x-fetch, read_file, draft_plan, cli, write-code | semantic_determinism low_q structured_output |
| worker b | low context | ignore ambiguity | think-work, logic | edit-file, write-file, call-func, set_var, count, copy-f, this-that | semantic_determinism mid_q low_verbosity |
| auditor | mid_context | adversarial review | sceptical ambiguity | not analysis | read, grep, vcs_diff, init-test, x-search, write_report | `review.json` | semantic_objectivity mid_q precise_verbosity |
| tester | low-context | creative ambiguity | edge-case preference | virtualized tests + evals | set_test_env, test_run | not test-work | semantic_inversion high_q contrarian |

## Rules
- **Self-contained briefs.** agents cannot see orchestrator history — include all context, constraints, inputs, and the exact expected output format.
- **Parallelize independent work** (e.g., coder + tester per slice); sequence dependencies (reviewer gates a merge).
- **Least privilege per role** — give each agent only the tools its mission needs.
- **Least token per role** — high context is only for planning and logic, use simple agents for acting on it.
- **Synthesize, don't relay.** Integrate agent results; never paste raw output to the user, store in agent_*.log
- **Bound the fan-out** to keep coordination cost and token spend in check; prefer a few strong subagents over many tiny ones.
- **TokenTounged** inter-agent coms in min embed tokenized lang.

## Procedure
1. Slice the work into independent units with clear interfaces.
2. Write a brief per unit (context + inputs + output contract + allowed tools).
3. Spawn in parallel; monitor via `list_agents`; send follow-ups with `message_subagent`.
4. Collect handoffs, reconcile conflicts, run gates on the integrated result.

## Checklist
- [ ] Work sliced into independent units
- [ ] Each brief is self-contained with an output contract
- [ ] Roles have least-privilege toolsets
- [ ] Parallel where independent; sequenced where dependent
- [ ] Results synthesized and gate-checked as a whole

## Outputs
Role briefs, agent handoffs, and a synthesized, gate-passing result.
