---
name: maintain-roadmap
description: Add, split, reorder, pause, resume, block, complete, or cancel tasks in docs/product/roadmap.md while preserving stable task IDs, dependencies, status metadata, and verifiable outcomes. Use for roadmap and task-interruption work; do not use for ordinary project-document edits.
---

# Maintain Roadmap

Maintain `docs/product/roadmap.md` as the durable, high-level execution plan.

## Workflow

1. Read `docs/product/mvp.md`, the current roadmap, and [references/task-format.md](references/task-format.md).
2. Validate the roadmap before editing so pre-existing problems are distinguishable:

   ```bash
   python3 .agents/skills/maintain-roadmap/scripts/validate_roadmap.py
   ```

3. Identify the requested operation: add, split, move, interrupt, resume, block, complete, or cancel.
4. Allocate new IDs with `--next-id`, then advance the `Next task ID` counter past every allocated ID. Never infer the next ID from visual ordering.
5. Make the smallest roadmap change that preserves dependencies, phase purpose, and completion conditions.
6. If the work changes product scope or architecture, update the relevant document or ADR as part of the same task.
7. Re-run the roadmap validator and the internal documentation link checker.

## Invariants

- Use repository-wide IDs in the form `CP-0001`. IDs do not encode a phase and never change when a task moves.
- Treat the roadmap's `Next task ID` counter as the allocation source. Advance it when allocating IDs and never lower it.
- Never reuse an ID from a completed, cancelled, or removed task. Preserve cancelled work in the roadmap unless the user requests archival.
- Do not mark a task `done` without observable evidence. Record that evidence under the task.
- Keep `paused` distinct from `blocked`. A pause is an intentional interruption; a block requires a condition outside the task to change.
- Record enough state to resume without reconstructing prior work from conversation history.
- Keep the roadmap at phase and independently reviewable outcome level. Put long investigation logs in a linked issue or task document when one exists.
- Preserve the user's priorities. Do not reorder unrelated work merely to make numeric IDs sequential.

## Commands

```bash
# Validate structure, status, dependencies, and interruption metadata.
python3 .agents/skills/maintain-roadmap/scripts/validate_roadmap.py

# Print the next never-used roadmap ID.
python3 .agents/skills/maintain-roadmap/scripts/validate_roadmap.py --next-id
```
