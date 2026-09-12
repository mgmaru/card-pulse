---
name: start-task
description: Start work on a roadmap task by creating its branch from an up-to-date main, and finish it through a pull request that CI has passed. Use when beginning or completing a CP-NNNN task; do not use for inspecting the repository without changing it.
---

# Start Task

`main` is protected. Every change reaches it through a branch and a pull request whose CI
has passed. This skill executes that loop.

[CONTRIBUTING.md](../../../CONTRIBUTING.md#ブランチとpull-request) is the source of truth for
the rules. Read it when a situation is not covered here, and change it rather than this
skill when a rule changes.

## Starting

1. Identify the roadmap task ID. If the work has no task, allocate one with
   [`maintain-roadmap`](../maintain-roadmap/SKILL.md) before branching.
2. Refuse to start on a dirty tree. Report uncommitted changes and let the user decide.
3. Create the branch from the current `main`:

   ```bash
   git switch main
   git pull --ff-only
   git switch -c cp-<id>-<summary>
   ```

   The summary is lowercase kebab-case, derived from the task line, not from the phase.

4. Set the task to `in-progress` with `maintain-roadmap` when the work spans more than a
   single session, so another session can resume it.

## Finishing

1. Run the validators the change requires. At minimum, documentation changes need the
   link checker, roadmap changes need the roadmap validator, and agent or skill changes
   need the tool parity check.
2. Record evidence and set the task to `done` with `maintain-roadmap`.
3. Commit, push, and open the pull request:

   ```bash
   git push -u origin cp-<id>-<summary>
   gh pr create --fill
   ```

4. Wait for CI, then merge with a merge commit:

   ```bash
   gh pr checks --watch
   gh pr merge --merge
   ```

   `--merge` is the only permitted method. `--squash` and `--rebase` are disabled on the
   repository and will fail.

5. Leave the branch in place. Do not pass `--delete-branch`, and do not offer to clean it
   up afterwards.

## When `main` has moved

Rebase the branch onto `main` and force-push with a lease, rather than merging `main` into
the branch:

```bash
git fetch origin
git rebase origin/main
git push --force-with-lease
```

This keeps the merge commit a clean boundary around the task. Rebasing is safe here only
because work branches are not shared; stop and ask if someone else has based work on the
branch.

## Boundaries

- Merging is the user's decision. Open the pull request and report its URL and CI status;
  ask before merging unless the user has already said to merge.
- Never push to `main` directly, and never bypass the ruleset, even when the change is
  trivial or CI is failing for an unrelated reason.
- One task per branch. If unrelated work appears mid-task, follow the interruption
  procedure in `maintain-roadmap` instead of widening the branch.
- This skill does not judge whether the change itself is correct. Review and testing
  remain the responsibility of the task being performed.
