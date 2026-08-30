procedure: procedure-authoring
procedure_version: 1.0.0
uses: [fs_read, fs_write]
procedure-authoring
Purpose
Write a procedure that binds a method to a piece of work, and prove it was needed.
Applies to
Work where the same skill can be used several correct ways and the difference matters.
Work whose failure is silent, ordered, or compared across agents.
A method already being repeated informally by more than one agent.
Not for single-step work whose failure announces itself. Read a named file, archive an artifact, fetch a known URL — the skill covers those, and a procedure over them is ceremony.
Not for anything a linter could enforce. That is a style, and style is a negative constraint while a procedure is a positive one.
Uses
fs_read — read the tool manifest, the skills for every tool named, and any sibling procedure this one competes with.
fs_write — write the procedure file.
Method
Name the drift trigger. D1 order dependence, D2 tempting shortcut, D3 silent failure, D4 downstream contract, D5 multi-agent consistency. If no trigger applies, stop and write nothing. An unnecessary procedure is a constraint with no defect behind it, and it will be followed anyway.
Name the procedure for its method, not its tool. inspect-workspace, never fs_read-inspect. A procedure named after a tool has collapsed into that tool's skill.
With fs_read, read the skill file for every tool you intend to name. Do not restate what it says; the skill describes the tool, this describes the work.
List in uses only the tools the method actually requires. Every tool listed will be provisioned. A tool that appears here and is never used in the Method is an unnecessary capability granted to every agent that runs this.
Write the Method as ordered steps a tired reader can follow without inference. Where order carries the guarantee, say why — an unexplained sequence gets reordered by whoever thinks they see a faster path.
Write Standards as conditions someone can check. A standard that restates a tool's effects is not a standard; a read-only tool not writing is a fact about the tool.
Write at least one bullet in Applies to saying when to choose a sibling instead. A procedure that never declines is a default wearing a name.
Read the sibling procedures for the same work with fs_read. If yours differs only in wording, amend theirs instead of adding a second.
Write the file with fs_write, then run the oracle. A procedure that has not been checked is a draft.
Standards
Exactly one drift trigger named, and it must be defensible in one sentence.
Every tool in uses appears in at least one Method step.
Every tool in uses has a skill file.
Method has four or more steps, in a fixed order.
At least one Standards line carries a number or an absolute, and none of them restate an effect.
Applies to states one condition under which this is the wrong choice.
Under 800 words. Long is unread, and unread is undone.
No shell command anywhere. Commands are data and live under style/.
Outputs
One procedure file, written with fs_write, passing the procedure oracle.
The named drift trigger, recorded so a later reviewer can judge whether it still holds.
Where an existing procedure was amended instead, a note saying so and why a second was not warranted.
