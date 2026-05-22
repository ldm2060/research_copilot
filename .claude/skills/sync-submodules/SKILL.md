---
name: sync-submodules
description: Update all third-party skill submodules under third_party/ to their latest upstream commits, report changes, and detect/categorize sync failures. Use when third-party skills look stale, after a fresh clone, or when CI reports submodule mismatches. The project has 17+ submodules from independent maintainers and conflicts are common.
disable-model-invocation: true
---

# sync-submodules

Pull the latest commits for every `third_party/*` submodule, summarize updates, and surface conflicts.

## When to use

- After a fresh `git clone` (use `--recurse-submodules`, or run this skill)
- Before a release build (ensure third-party skills are current)
- When a third-party skill is missing a feature documented upstream
- When CI reports "submodule HEAD does not match"

## Workflow

### 1. Snapshot current state

```bash
git submodule status > .tmp/submodule-status.before.txt
```

### 2. Update all submodules

```bash
git submodule sync --recursive
git submodule update --init --recursive --remote
```

`--remote` fetches each submodule's tracked branch (default: the branch set in `.gitmodules`, falling back to the default branch).

### 3. Diff against snapshot

```bash
git submodule status > .tmp/submodule-status.after.txt
diff .tmp/submodule-status.before.txt .tmp/submodule-status.after.txt
```

Lines beginning with `-` are old commits; `+` are new commits. The hash prefix tells you each submodule's new HEAD.

### 4. Categorize the changes

For each updated submodule, classify the change:

| Marker in `git submodule status` | Meaning | Action |
|-----------------------------------|---------|--------|
| ` <hash> path (tag)` | Clean update | Commit the bump |
| `+<hash> path` | Local modifications | Inspect `git -C path status`, decide whether to reset or commit |
| `-<hash> path` | Submodule not initialized | Run `git submodule update --init path` |
| `U<hash> path` | Merge conflict | Resolve inside the submodule, then `git add path` from repo root |

### 5. Verify build still works

After bumping submodules, run the `validate-plugin-build` skill to catch breakages early. Submodule bumps frequently break the `dist/` build because upstream skills rename files.

### 6. Commit the bump

```bash
git add third_party/
git commit -m "chore: bump third-party submodules

$(git submodule summary)
"
```

## Submodules currently tracked

The 17 third-party submodules live under `third_party/` — see `.gitmodules` for the canonical list. Notable ones:
- `superpowers` — core workflow skills (most active)
- `anthropics` — official Anthropic skill bundle
- `k-dense-ai` — claude-scientific-skills
- `orchestra` — AI-Research-SKILLs
- `auto-research` — wanshuiyin's research automation

## Failure recovery

| Symptom | Fix |
|---------|-----|
| `fatal: remote error: upload-pack: not our ref` | Submodule pointed at a deleted commit — edit `.gitmodules` to track the default branch instead |
| `Authentication failed` on a Gitee mirror | Some submodules are GitHub-only; skip them on Gitee builds |
| Local edits in submodule | `git -C third_party/<name> stash` before resyncing |
| Network timeout | Set `GIT_HTTP_LOW_SPEED_LIMIT=0`, retry, or skip with `--single-branch` |

## Related

- After sync → run `validate-plugin-build` to confirm `dist/` still builds
- For a single submodule → use `git submodule update --remote third_party/<name>` directly
