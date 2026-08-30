# Analysis Report: /var/home/simon/work/escendit/sandbox-bmad/skills/gzp-pipeline

Generated: 2026-08-30T10:15:00+02:00 · Schema: 2

**Grade: Excellent**

> All 6 findings from the 5-lens scan were fixed in this same build session — including one high-severity schema bug (open_time_log couldn't actually support the concurrent sessions issue-report.md promises) and one medium (current_task.step declared and branched on but never written). Post-fix, quick_validate/scan-scripts/prepass-workflow-integrity and all unit tests pass clean. The high-severity concurrency fix (enhancement-1) was independently re-verified against the shipped code on a follow-up pass — schema, commands, references, and tests all confirmed consistent, no regression.

gzp-pipeline is a lean, well-bounded single skill (SKILL.md at 1213 tokens, well under budget) with a clean intelligence/script boundary and no customization-surface issues. The Enhancement lens caught a real concurrency bug in the session-state schema before it could bite in production — primary-task and issue-task time-log sessions would have silently clobbered each other — which is now fixed with a task_id-keyed schema and dedicated open-time-log/close-time-log commands.

| Severity | Count |
| --- | --- |
| Critical | 0 |
| High | 1 |
| Medium | 2 |
| Low | 3 |

## Themes

### 1. Session-state schema didn't match the concurrency the prose promised

- Root cause: issue-report.md was written to describe a primary task and an issue task each holding their own independent time-log session, but the underlying session_state.py schema only had room for one open session at a time — the second open-time-log call would have silently overwritten the first.
- Fix: Rekey open_time_logs by task_id (done) so the schema can actually hold what the prose already claimed.
- Findings:
  - `enhancement-1` Add: concurrent-session support for session-state's single-slot open_time_log — `references/issue-report.md:11 vs scripts/session_state.py schema / references/time-log-session.md:19`

### 2. A resume-condition field that nothing ever wrote

- Root cause: current_task.step was reserved in the schema and read by SKILL.md's resume check, but no reference file's procedure ever called set on it, so that half of resume detection was permanently dead.
- Fix: Write current_task.step at each real checkpoint in task-loop.md (done): in_progress, pr_open_awaiting_merge, addressing_review_feedback.
- Findings:
  - `enhancement-2` Add: wire current_task.step, or drop it — it's declared and branched on but never written — `scripts/session_state.py schema and SKILL.md resume condition vs references/task-loop.md`

### 3. Two small path/self-containment slips

- Root cause: A config path was written as a bare filename instead of the full {project-root} path (breaking the skill's own Resolution rules), and a carved reference file pointed back at SKILL.md for a rule instead of restating it, which breaks under context compaction.
- Fix: Fully qualify the config.user.yaml path; restate the GPG rule inline in task-loop.md. Both done.
- Findings:
  - `architecture-1` Unqualified .user.yaml path breaks Resolution rules — `SKILL.md On Activation step 1`
  - `architecture-2` task-loop.md leans on SKILL.md for the GPG invariant — `references/task-loop.md step 5`

## Strengths

- Clean intelligence/script boundary: session_state.py owns all deterministic state CRUD, judgment (feedback triage, ambiguity resolution, bot-finding verification) stays in prompts, and the wall-clock date call correctly stays inline bash rather than a needless script wrapper.
- No customize.toml, by deliberate logged decision — the module-config read at activation is correctly not treated as a customization surface.
- Progressive disclosure is sound: SKILL.md carries the overview, invariants, and routing table; capability-specific procedure is carved to references/ with no other back-references to SKILL.md remaining after the fix.
- The six cross-cutting invariants (sole Zoho-writer, issues-aren't-work-items, one-task-at-a-time, GPG hard checkpoint, non-code skips GitHub Flow, never fabricate verification) correctly stay in SKILL.md rather than being buried in a reference only some branches would load.

## Recommendations

1. None outstanding — all 6 findings were fixed in this session. When live eval auth (ANTHROPIC_API_KEY) is available, run the staged evals/cases.json (baseline mode) and evals/queries.json (trigger mode) to get a real behavioral verdict beyond static analysis.

## Experience

- **Start a phase, work it to close** — Start a new phase (references/planning-phase.md) → Work a task through GitHub Flow or the non-code path (references/task-loop.md) → resume cleanly after an interruption via session-state.json
- **Something breaks mid-task** — Report an issue (references/issue-report.md) → standalone Zoho task + independent time-log session, tracked separately from the primary task
- Headless: No headless mode — interactive only by design, since GPG verification and merge confirmation are deliberate human-in-the-loop checkpoints on a skill driving real external systems.

## Findings

### High (1)

#### enhancement-1 — Add: concurrent-session support for session-state's single-slot open_time_log

- Lens: enhancement
- Location: `references/issue-report.md:11 vs scripts/session_state.py schema / references/time-log-session.md:19`
- Evidence: session-state's open_time_log was a single object, not keyed — issue-report.md promised the originating task's open session and a new issue-task's open session could coexist, but a second open-time-log call would silently overwrite the first, and the dangling-session check would misfire and force-close a still-legitimate session.
- Recommendation: Fixed: open_time_logs is now a dict keyed by task_id, with dedicated open-time-log/close-time-log commands that fail loud on a duplicate open or a missing close target, so two tasks' sessions genuinely coexist.

### Medium (2)

#### enhancement-2 — Add: wire current_task.step, or drop it — it's declared and branched on but never written

- Lens: enhancement
- Location: `scripts/session_state.py schema and SKILL.md resume condition vs references/task-loop.md`
- Evidence: SKILL.md's resume logic branches on current_task.step being mid-flight, but no reference file ever set it — the field was permanently null.
- Recommendation: Fixed: task-loop.md now sets current_task.step at in_progress, pr_open_awaiting_merge, and addressing_review_feedback checkpoints for both the code and non-code paths.

#### architecture-1 — Unqualified .user.yaml path breaks Resolution rules

- Lens: architecture
- Location: `SKILL.md On Activation step 1`
- Evidence: Config load referenced bare '.user.yaml' instead of the full {project-root}/_bmad/config.user.yaml path used everywhere else in the skill and by sibling skills sharing this config pattern.
- Recommendation: Fixed: now reads {project-root}/_bmad/config.user.yaml explicitly.

### Low (3)

#### architecture-2 — task-loop.md leans on SKILL.md for the GPG invariant

- Lens: architecture
- Location: `references/task-loop.md step 5`
- Evidence: The GPG rule was referenced as 'see the GPG invariant in SKILL.md' instead of being restated, which breaks self-containment since SKILL.md can drop from context mid-flow.
- Recommendation: Fixed: the operative rule (never override commit.gpgsign, never --no-gpg-sign, stop-and-ask on an unverifiable signature) is now stated inline.

#### leanness-1 — Invariants preamble narrates the system to itself rather than instructing

- Lens: leanness
- Location: `SKILL.md Invariants intro sentence`
- Evidence: The framing clause ('what flaky looked like before this skill existed') described the skill's own history without changing how any of the six bullets are applied.
- Recommendation: Fixed: trimmed to a plain lead-in; the bullets carry all the binding force.

#### leanness-2 — Duration-is-derived fact stated twice in time-log-session.md

- Lens: leanness
- Location: `references/time-log-session.md`
- Evidence: The 'Zoho derives the duration, don't compute it yourself' fact was stated once in the opening paragraph and again as a bolded rule near the Stop step.
- Recommendation: Fixed: kept only at the actionable point of use (the bolded Stop-step rule).
