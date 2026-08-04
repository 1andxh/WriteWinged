# Agent instructions

- Never run `git commit`, `git push`, `git revert`, or any `gh` command (including `gh pr merge`) unless the user's request explicitly asks for that action in this exact turn. Reviewing, analyzing, or reading code is never itself permission to commit, push, or merge it.
- If you're asked to review a diff or working-tree changes, treat that as read-only: report findings, do not stage, commit, or modify files, and do not run any command that mutates git state or GitHub state.
- If you believe a change should be committed, say so and wait for explicit confirmation instead of doing it.
