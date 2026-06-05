# Research Copilot Workflow

[workflow-state:no_task]
No active task. Either answer directly, or run `rc task create --kind <k> --title "<t>"` to start one. Consult [research-state] for recommended next activities.
[/workflow-state]

[workflow-state:planning]
Active task is in PLANNING. Use the rc-plan helper to clarify it into prd.md and curate execute.jsonl / verify.jsonl. Then `rc task start <id>`.
[/workflow-state]

[workflow-state:in_progress]
Active task is IN PROGRESS. Dispatch the rc-{kind} executor with prd.md + execute.jsonl specs. Do NOT do domain work inline. When the executor returns, run `rc task verify <id>`.
[/workflow-state]

[workflow-state:verify]
Active task is in VERIFY. Dispatch rc-verify to run the kind's quality gate. On pass: `rc task complete <id>`. On fail: fix and `rc task set-status <id> in_progress`.
[/workflow-state]

[workflow-state:completed]
Active task COMPLETED. Run rc-update-spec to sediment learnings into spec/, append a journal entry, then consult [research-state] for the next activity.
[/workflow-state]
