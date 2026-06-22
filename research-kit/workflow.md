# Research Copilot Workflow

MAIN SESSION = Trellis conductor. Every research-domain action must belong to a .research/tasks/<id> task node and be executed by the legal rc-* leaf executor for that node's current lifecycle state and kind. The conductor advances the frontier; it does not consume the frontier itself. Do not consume the frontier yourself.

[workflow-state:no_task]
No active task node. If the user asks for research-domain work and there is no active task, create a task node first with `rc task create --kind <k> --title "<t>"`, publish the orchestration task list, then dispatch `rc-plan`. If the user asks for repository development or general explanation, answer normally without creating a research task.
[/workflow-state]

[workflow-state:planning]
Active task is in PLANNING. The only legal research executor is `rc-plan`. Dispatch `rc-plan` with task id, kind, status, input context, expected `prd.md` / `execute.jsonl` / `verify.jsonl`, and the no-recursive-dispatch rule. When `rc-plan` returns with planning artifacts, run `rc task start <id>`.
[/workflow-state]

[workflow-state:in_progress]
Active task is IN PROGRESS. Dispatch the kind-specific leaf executor: literature → `rc-literature`, ideation → `rc-ideation`, experiment → `rc-experiment`, writing → `rc-writer`, polish → `rc-polisher`, review → `rc-reviewer`, rebuttal → `rc-rebuttal`. Provide `prd.md`, `execute.jsonl`, task id, ownership paths, and gap reporting expectations. Do not do domain work inline. When the executor returns, run `rc task verify <id>`.
[/workflow-state]

[workflow-state:verify]
Active task is in VERIFY. The only legal research executor is `rc-verify`. Dispatch `rc-verify` to run the kind's quality gate. On pass: `rc task complete <id>`. On fail: record gaps, run `rc task set-status <id> in_progress`, and dispatch the kind executor for repair.
[/workflow-state]

[workflow-state:completed]
Active task COMPLETED. The only legal research executor is `rc-update-spec`. Dispatch `rc-update-spec` to sediment learnings into `.research/spec/`, append a journal entry, and surface gap-driven recommendations. Then consult [research-state] to decide whether to create the next Trellis node or report completion to the user.
[/workflow-state]
