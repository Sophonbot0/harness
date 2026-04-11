# Sprint Architecture Analysis — Harness System

**Date:** 2026-03-27  
**Type:** Architecture Analysis (no implementation)  
**Author:** Planner/Architect Agent

---

## Table of Contents

1. [Problem Restatement](#1-problem-restatement)
2. [Current Architecture Constraints](#2-current-architecture-constraints)
3. [Sprint Splitting Strategy](#3-sprint-splitting-strategy)
4. [Sprint Execution Flow](#4-sprint-execution-flow)
5. [Context Management Strategy](#5-context-management-strategy)
6. [Plugin Integration Design](#6-plugin-integration-design)
7. [State Persistence Design](#7-state-persistence-design)
8. [Concrete Example: 20-Feature Project](#8-concrete-example-20-feature-project)
9. [Risk Assessment](#9-risk-assessment)
10. [Final Recommendation & MVP](#10-final-recommendation--mvp)

---

## 1. Problem Restatement

The current harness runs a single PLAN→BUILD→CHALLENGE→EVAL cycle for the entire project. This works for 3–8 feature projects. For larger projects (10–50+ features, 20–100+ DoD items), four problems emerge:

| Problem | Root Cause | Symptom |
|---|---|---|
| **Token overhead** | plan.md + eval-report.md + challenge-report.md grow linearly with features | Context fills up, agent loses early context, quality drops |
| **Subagent context limits** | Generator subagent gets full plan + all code + eval feedback | >50 DoD items = the generator can't hold everything and rushes |
| **Quality degradation** | Too many things to build at once | Shallow implementation, missed edge cases, stubs |
| **All-or-nothing delivery** | Single eval pass/fail for the whole project | 19/20 features pass but 1 fails = entire run fails, no incremental value |

The owner wants the planner to have **no cap on features** — a complex project can be as big as it needs to be. The solution is to **chunk execution into sprints** while keeping the master plan complete.

---

## 2. Current Architecture Constraints

Before designing the sprint system, these are the hard constraints from the existing code:

### 2.1 Plugin State Model

From `src/state.ts`, `RunState` tracks:
```typescript
interface RunState {
  runId: string;
  planPath: string;      // single plan file
  taskDescription: string;
  startedAt: string;
  phase: string;         // single current phase
  round: number;         // single round counter
  checkpoints: string[];
  status: "active" | "completed" | "failed" | "cancelled";
}
```

**Key constraint:** The model assumes one plan, one phase, one round counter. There is no concept of "sprint N of M." This must be extended.

### 2.2 Single Active Run

`findActiveRun()` scans all run directories and returns the first with `status: "active"`. `harness_start` rejects if an active run exists. This means sprints must either:
- (A) Be sequential runs (complete Sprint 1, start Sprint 2 as a new run), or
- (B) Be sub-runs within a single master run

### 2.3 harness_submit Validation

`harness_submit` checks:
1. Eval report says "Overall: PASS"
2. All DoD items in plan.md are checked (`- [x]`)
3. No unaddressed CRITICAL challenges

**Key constraint:** It validates ALL DoD items in the plan. For sprints, it would need to validate only the current sprint's DoD items, or the plan would need to be sprint-scoped.

### 2.4 Subagent Limitations

- Subagents run with `thinking: "off"` (crash with 400 otherwise)
- Generator timeout: 45 min
- Subagents get clean context (no carry-over from prior subagents)
- Subagents CAN read/write the filesystem (the code exists on disk)

### 2.5 Progress Bar

`renderProgressBar` shows a single phase pipeline (`plan→build→challenge→eval`) and a flat feature list. No sprint concept exists.

---

## 3. Sprint Splitting Strategy

### 3.1 When to Split

**Recommended threshold:** Split when the plan has **>8 features OR >25 DoD items.**

| Project Size | Features | Typical DoD Items | Strategy |
|---|---|---|---|
| Small | 1–4 | 5–15 | Single cycle, no sprints |
| Medium | 5–8 | 16–25 | Single cycle, might benefit from sprints |
| Large | 9–15 | 26–50 | **Split into 2–4 sprints** |
| XL | 16–30 | 51–100 | **Split into 4–8 sprints** |
| Massive | 31–50+ | 100+ | **Split into 8–15 sprints** |

**Why 8 features?** The generator subagent performs well with 3–5 features in focus. At 8 features (typically ~25 DoD items), the eval report alone starts consuming 2–3K tokens. Beyond that, quality degrades measurably.

**Why not a hard rule?** The planner should evaluate complexity, not just count. Four complex features with 8 DoD items each (32 total) should split. Eight trivial features with 2 DoD items each (16 total) might not need to.

### 3.2 How to Group Features into Sprints

**Primary criterion: Dependency order.** Features that depend on others go in later sprints.

**Secondary criterion: Domain cohesion.** Group features that touch the same files/modules.

**Tertiary criterion: Priority.** Higher-priority features go in earlier sprints (so if the project is abandoned mid-way, the most valuable work is done).

#### Grouping Algorithm (for the planner to follow)

```
1. Build a dependency graph of features
2. Topological sort → get dependency layers
3. Group features within the same dependency layer by domain affinity
4. Pack into sprints of 3–5 features each
5. If a sprint has >6 features, split by domain
6. If a sprint has <2 features, merge with adjacent sprint
```

### 3.3 Optimal Sprint Size

**Target: 3–5 features, 10–18 DoD items per sprint.**

| Sprint Size | Pros | Cons |
|---|---|---|
| 1–2 features | Very focused | Overhead: each sprint is a full PLAN→BUILD→CHALLENGE→EVAL cycle |
| **3–5 features** | **Sweet spot: manageable, focused, good signal** | — |
| 6–8 features | Fewer sprints, less overhead | Starts approaching the quality-drop zone |
| 9+ features | Not a sprint, it's the original problem | Don't do this |

**Hard cap: No sprint should exceed 7 features or 25 DoD items.** If the planner produces a sprint larger than this, the orchestrator should split it.

---

## 4. Sprint Execution Flow

### 4.1 Architecture Overview

```
MASTER PLAN (plan.md — all features, sprint assignments, full DoD)
│
├─ harness_start (masterPlanPath, taskDescription, sprintCount=4)
│
├─ Sprint 1 (Features 1-4) ──────────────────────────────────
│   ├─ [Sprint plan extracted: sprint-1-plan.md]
│   ├─ PLAN (planner reviews sprint scope — lightweight, may skip)
│   ├─ BUILD (generator gets sprint-1-plan.md only)
│   │   └─ harness_checkpoint(sprint=1, phase="build", ...)
│   ├─ CHALLENGE (adversary gets sprint-1 scope + code)
│   │   └─ harness_checkpoint(sprint=1, phase="challenge", ...)
│   ├─ EVAL (evaluator gets sprint-1 DoD only)
│   │   └─ harness_checkpoint(sprint=1, phase="eval", ...)
│   ├─ PASS? → mark sprint 1 complete, commit
│   └─ FAIL? → retry loop (same as current, max 2 retries)
│       └─ STUCK? → escalate Sprint 1 to owner, don't proceed
│
├─ Sprint 2 (Features 5-8) ──────────────────────────────────
│   ├─ [Sprint plan extracted: sprint-2-plan.md]
│   ├─ Context briefing: "Sprint 1 completed: [summary]. Code on disk."
│   ├─ BUILD → CHALLENGE → EVAL
│   ├─ PASS? → mark sprint 2 complete
│   └─ FAIL? → retry / escalate
│
├─ Sprint 3 (Features 9-12) ─────────────────────────────────
│   └─ ... same pattern ...
│
├─ Sprint 4 (Features 13-16) ────────────────────────────────
│   └─ ... same pattern ...
│
└─ INTEGRATION (Optional — see §4.3)
    ├─ Lightweight CHALLENGE across all features
    ├─ Integration EVAL: cross-sprint interactions
    └─ harness_submit (master plan, final eval)
```

### 4.2 Key Design Decisions

#### Q: Does each sprint get its own plan.md?

**Yes — each sprint gets a sprint-scoped plan file (e.g., `sprint-1-plan.md`).**

Rationale:
- The generator subagent only sees the sprint plan (3–5 features, ~15 DoD items) — fits comfortably in context
- The evaluator only validates the sprint's DoD items — focused evaluation
- The master plan stays intact as the source of truth with sprint status markers
- `harness_submit` for a sprint validates against the sprint plan, not the master plan

The orchestrator (main agent) extracts sprint plans from the master plan. This is a text operation, not a subagent task.

#### Q: How does the orchestrator track cross-sprint progress?

**The master plan gets updated in place with sprint completion markers:**

```markdown
## Sprint 1: Foundation ✅ (completed 2026-03-27T14:30:00Z)

### Feature 1: Database Schema ✅
- [x] DoD item 1
- [x] DoD item 2

### Feature 2: API Routes ✅
- [x] DoD item 1
- [x] DoD item 2

## Sprint 2: Business Logic ⏳ (in progress)

### Feature 5: Validation Engine
- [ ] DoD item 1
- [ ] DoD item 2
```

The plugin tracks this in `run-state.json` with a new `sprints` array (see §6).

#### Q: What happens if Sprint 2 needs to modify Sprint 1's code?

**This is expected and allowed.** Sprint 2's generator has full filesystem access. It can modify Sprint 1's code. The key rule is:

1. Sprint 2's eval only checks Sprint 2's DoD items
2. If Sprint 2 breaks Sprint 1's functionality, the **integration eval** (§4.3) catches it
3. The sprint plan can explicitly note: "This sprint modifies Feature 1's schema (from Sprint 1) — ensure backward compatibility"

**Mitigation:** The planner should front-load foundational features (schemas, types, core abstractions) into Sprint 1 and structure later sprints to extend rather than refactor. If the planner knows Feature 8 will change Feature 2's API, they should be in the same sprint.

#### Q: Should there be a final integration eval?

**Yes, but only if the project has >2 sprints.** For 2-sprint projects, the overhead isn't worth it.

The integration eval is lightweight:
- No separate BUILD phase
- Adversary runs across all code (full scope)
- Evaluator checks: (a) all DoD items still pass, (b) cross-feature interactions work, (c) no regressions
- If integration eval fails, a targeted fix cycle runs (only fixing the broken interactions)

### 4.3 Integration Eval Design

```
INTEGRATION EVAL (after all sprints pass)
├── Read: master plan (all DoD items)
├── Read: all code (full project)
├── ADVERSARY: focus on cross-feature interactions
│   "These features were built in separate sprints. Find integration gaps."
├── EVALUATOR: 
│   - Re-run all tests (full test suite)
│   - Check cross-sprint data flows
│   - Verify no regressions from later sprints
├── PASS? → harness_submit with master plan
└── FAIL? → targeted fix cycle (generator gets only the failing items)
```

**When to skip integration eval:**
- Project has ≤2 sprints
- All features are independent (no cross-feature data flows)
- Total DoD items ≤20 (small enough for a single eval to be reliable)

### 4.4 Sprint Re-Planning

Between sprints, the orchestrator should check:

1. **Did the sprint change the architecture?** If Sprint 1 introduced an unexpected pattern, later sprint plans might need adjustment.
2. **Did the sprint reveal new requirements?** The adversary might uncover gaps that affect future sprints.
3. **Did the owner provide feedback?** Between sprints is a natural point for owner input.

If re-planning is needed, the orchestrator can re-run the planner for the remaining sprints only. The master plan is updated, but completed sprints are not touched.

---

## 5. Context Management Strategy

This is the most critical design decision. Each subagent starts fresh. How does Sprint 2's generator know what Sprint 1 built?

### 5.1 Options Analysis

| Option | Token Cost | Completeness | Risk |
|---|---|---|---|
| A. Pass summary of prior sprints | ~200–500 tokens | Low — misses details | Generator may miss context, make incompatible decisions |
| B. Let subagent read codebase | 0 tokens passed, but ~5 min reading time | High — code is on disk | Slower startup, might read wrong files |
| C. Pass master plan with checked items | ~1K–3K tokens | Medium — shows what's done | Doesn't show HOW it was done |
| **D. Hybrid: brief + guided reading list** | ~300–600 tokens | High | Best tradeoff |

### 5.2 Recommended Approach: Option D — Hybrid Briefing

Each sprint's generator gets:

```markdown
## Prior Sprint Context

### Sprint 1: Foundation ✅
Built: Database schema (User, Team, Project models), API routes (/api/users, /api/teams), 
Authentication middleware (JWT-based, see src/middleware/auth.ts).
Key files: src/models/*.ts, src/routes/*.ts, src/middleware/auth.ts

### Sprint 2: Business Logic ✅
Built: Validation engine, Notification system, Permission checks.
Key files: src/services/validator.ts, src/services/notifier.ts, src/middleware/permissions.ts

### Your Sprint (Sprint 3): UI Components
[full sprint-3-plan.md follows]
```

This gives the generator:
1. **What was built** (summary, ~100 tokens per completed sprint)
2. **Where to find it** (key files, so the generator can read them if needed)
3. **Full focus** on the current sprint's plan (unchanged from single-sprint approach)

### 5.3 Token Budget Per Sprint

| Component | Tokens (estimated) |
|---|---|
| Sprint plan (3–5 features) | 800–1,500 |
| Prior sprint summaries (~150 per sprint) | 0–1,500 (for up to 10 prior sprints) |
| Eval feedback (if retry round) | 500–1,000 |
| Challenge report (if retry round) | 500–1,000 |
| **Total input to generator** | **1,300–5,000** |

Compare to current monolithic approach for a 20-feature project:
- Full plan: 5,000–8,000 tokens
- Full eval report: 3,000–5,000 tokens
- Full challenge report: 2,000–3,000 tokens
- **Total: 10,000–16,000 tokens**

**Sprints reduce generator input by 3–10x**, leaving far more context window for the actual code.

---

## 6. Plugin Integration Design

### 6.1 RunState Extension

```typescript
interface RunState {
  runId: string;
  planPath: string;           // master plan path
  taskDescription: string;
  startedAt: string;
  phase: string;
  round: number;
  checkpoints: string[];
  status: "active" | "completed" | "failed" | "cancelled";
  
  // ─── NEW: Sprint fields ───
  sprintMode: boolean;        // true if project uses sprints
  totalSprints: number;       // total planned sprints
  currentSprint: number;      // 1-indexed current sprint
  sprintResults: SprintResult[];
}

interface SprintResult {
  sprintNumber: number;
  features: string[];         // feature names in this sprint
  dodItemCount: number;
  status: "pending" | "active" | "completed" | "failed";
  startedAt?: string;
  completedAt?: string;
  evalGrade?: string;
  rounds: number;             // how many BUILD→CHALLENGE→EVAL rounds this sprint took
  summary?: string;           // brief summary of what was built
  keyFiles?: string[];        // key files created/modified
}
```

### 6.2 Tool Changes

#### `harness_start` — Extended

New optional parameters:
```typescript
{
  planPath: string;           // master plan path (unchanged)
  taskDescription: string;    // unchanged
  // NEW:
  sprintMode?: boolean;       // default false (backward compatible)
  totalSprints?: number;      // required if sprintMode=true
  sprintDefinitions?: Array<{
    sprintNumber: number;
    features: string[];
    dodItemCount: number;
  }>;
}
```

If `sprintMode` is false, behavior is identical to current (full backward compatibility).

#### `harness_checkpoint` — Extended

New optional parameter:
```typescript
{
  phase: string;
  completedFeatures: string[];
  pendingFeatures: string[];
  blockers: string[];
  summary: string;
  // NEW:
  sprint?: number;            // which sprint this checkpoint is for
}
```

#### New Tool: `harness_sprint_complete`

```typescript
{
  sprint: number;
  evalGrade: string;
  summary: string;
  keyFiles: string[];
}
```

This marks a sprint as completed and advances `currentSprint`. It does NOT validate like `harness_submit` — sprint completion is recorded by the orchestrator after the eval passes.

#### `harness_submit` — Extended

For sprint-mode runs, `harness_submit` is called once at the very end (after all sprints + integration eval). It validates:
1. All sprint results show status "completed"
2. The final eval report passes
3. Master plan DoD items are all checked

#### `harness_status` — Extended

Output includes sprint progress:
```json
{
  "runId": "...",
  "sprintMode": true,
  "currentSprint": 2,
  "totalSprints": 4,
  "sprintResults": [
    { "sprintNumber": 1, "status": "completed", "evalGrade": "PASS", "rounds": 1 },
    { "sprintNumber": 2, "status": "active", "rounds": 1 }
  ],
  "latestCheckpoint": { ... }
}
```

#### `harness_reset` — Extended

New optional parameter:
```typescript
{
  reason?: string;
  scope?: "sprint" | "all";   // default "all"
}
```

- `scope: "all"` — cancels the entire run (current behavior)
- `scope: "sprint"` — resets only the current sprint (re-run it from BUILD), keeps prior sprint results

### 6.3 Progress Bar Extension

The progress bar should show sprint context:

```
🔧 Harness: Implement Company OS v2
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📦 Sprint 2/4 — Business Logic
●plan→▶build→○challenge→○eval
▰▰▰▰▰▰▰▰▰▰▱▱▱▱▱ 65% ⏱12m 34s

Sprint Features:
✅ Validation engine
⏳ Notification system
⬜ Permission checks

Sprints: ✅✅⏳⬜
DoD: 28/45 ✅ | Blockers: 0
```

Key additions:
- **Sprint N/M header** — which sprint, how many total
- **Sprint progress bar** — `✅✅⏳⬜` showing completed/active/pending sprints
- **Within-sprint features only** — don't show all 20 features, only the current sprint's 3–5
- **DoD total across all sprints** — so the owner sees overall project progress

Implementation in `src/progress.ts`:
```typescript
export interface SprintProgressBarParams extends ProgressBarParams {
  sprintMode: boolean;
  currentSprint: number;
  totalSprints: number;
  sprintStatuses: Array<"completed" | "active" | "pending">;
  overallDodTotal: number;
  overallDodCompleted: number;
}
```

---

## 7. State Persistence Design

### 7.1 File Structure

```
~/.openclaw/harness-enforcer/runs/{runId}/
├── run-state.json          # includes sprintMode, sprintResults
├── dod-items.json          # master DoD items
├── checkpoints.jsonl       # all checkpoints (tagged with sprint number)
├── delivery.json           # final delivery (after all sprints)
├── sprint-1/
│   ├── sprint-plan.md      # extracted sprint plan
│   ├── eval-report.md      # sprint 1 eval
│   └── challenge-report.md # sprint 1 challenges
├── sprint-2/
│   ├── sprint-plan.md
│   ├── eval-report.md
│   └── challenge-report.md
└── integration/
    ├── eval-report.md      # integration eval
    └── challenge-report.md # integration challenges
```

### 7.2 Sprint Plan Extraction

The orchestrator extracts sprint plans from the master plan. This is a string operation:

1. Read master plan
2. Find the sprint section: `## Sprint N: [Name]`
3. Extract all features under that sprint section
4. Write to `sprint-N/sprint-plan.md` with:
   - Sprint context header (what was done before)
   - Feature definitions (from master plan)
   - Sprint-scoped DoD items only

### 7.3 Cross-Sprint State

After each sprint completes, the orchestrator updates:
1. **Master plan** — check off completed DoD items (`- [ ]` → `- [x]`)
2. **run-state.json** — update sprintResults array
3. **Sprint summary** — written to `sprintResults[n].summary` for context briefing

This data survives context compaction because it's on disk. If the agent's context is compacted between sprints, the `before_prompt_build` hook can inject the current sprint status.

### 7.4 Recovery After Crash

If the process crashes mid-sprint:
1. `harness_status` reads `run-state.json` — shows which sprint was active
2. The orchestrator sees which sprint was in progress and its last checkpoint
3. The orchestrator can resume the current sprint from its last checkpoint phase
4. Completed sprints are not re-run (their code is committed and on disk)

---

## 8. Concrete Example: 20-Feature Project

### Project: "Company OS v2 — Full Platform Rebuild"

#### Master Plan Features:
1. Database schema (User, Team, Project, Task)
2. Authentication (JWT, refresh tokens)
3. Authorization (role-based, permissions)
4. User CRUD API
5. Team CRUD API
6. Project CRUD API
7. Task CRUD API
8. Real-time notifications (WebSocket)
9. Email notification service
10. Search engine (full-text)
11. File upload/storage
12. Audit log system
13. Dashboard API (aggregations)
14. API rate limiting
15. Health check endpoints
16. Admin panel API
17. Data export (CSV, JSON)
18. Webhook system
19. API documentation (OpenAPI)
20. Integration test suite

#### Sprint Splitting

**Dependency analysis:**
- Features 1–3 are foundational (everything depends on them)
- Features 4–7 are CRUD (depend on 1–3, independent of each other)
- Features 8–9 are notifications (depend on 1–3)
- Features 10–11 are data services (depend on 1)
- Features 12–14 are platform services (depend on 1–7)
- Features 15–16 are ops/admin (depend on 1–3)
- Features 17–18 are integrations (depend on 4–7)
- Features 19–20 are meta/quality (depend on everything)

**Sprint assignment:**

| Sprint | Features | DoD Items (est.) | Rationale |
|---|---|---|---|
| **Sprint 1: Foundation** | 1. Schema, 2. Auth, 3. Authz | ~12 | Everything depends on these. Must be solid. |
| **Sprint 2: Core CRUD** | 4. Users, 5. Teams, 6. Projects, 7. Tasks | ~16 | Cohesive domain, all follow same pattern. |
| **Sprint 3: Services** | 8. RT Notifications, 9. Email, 10. Search, 11. File Upload | ~16 | Data services layer. Independent of each other. |
| **Sprint 4: Platform** | 12. Audit Log, 13. Dashboard, 14. Rate Limiting, 15. Health Checks | ~14 | Cross-cutting platform concerns. |
| **Sprint 5: Extensions** | 16. Admin, 17. Export, 18. Webhooks | ~12 | Build on top of everything else. |
| **Sprint 6: Quality** | 19. API Docs, 20. Integration Tests | ~8 | Meta/quality sprint — validates everything. |

**6 sprints, average 3.3 features and ~13 DoD items per sprint.**

#### Execution Timeline (estimated)

| Sprint | BUILD | CHALLENGE | EVAL | Retries | Est. Time |
|---|---|---|---|---|---|
| Sprint 1 | 30 min | 10 min | 15 min | 1 retry | ~90 min |
| Sprint 2 | 35 min | 10 min | 15 min | 0 retries | ~60 min |
| Sprint 3 | 40 min | 12 min | 15 min | 1 retry | ~100 min |
| Sprint 4 | 30 min | 10 min | 15 min | 0 retries | ~55 min |
| Sprint 5 | 25 min | 10 min | 12 min | 0 retries | ~50 min |
| Sprint 6 | 35 min | 10 min | 15 min | 1 retry | ~90 min |
| Integration | — | 15 min | 20 min | 0 retries | ~35 min |
| **Total** | | | | | **~480 min (~8 hours)** |

Compare to monolithic approach: a 20-feature project in a single cycle would likely take 3–4 hours for BUILD alone, with significant quality degradation and a high chance of STUCK on multiple items. The sprint approach takes longer in wall time but delivers higher quality and provides incremental value.

#### Context Token Comparison

| Approach | Generator Input (tokens) | Generator Available Context |
|---|---|---|
| Monolithic (20 features) | ~12,000 | Severely constrained |
| Sprint 3 (4 features + summaries) | ~2,500 | Plenty of room |

#### What the Owner Sees (Telegram)

At Sprint 3:
```
🔧 Harness: Company OS v2 — Full Platform Rebuild
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📦 Sprint 3/6 — Services
●plan→●build→▶challenge→○eval
▰▰▰▰▰▰▰▰▰▱▱▱▱▱▱ 58% ⏱3h 12m

Sprint Features:
✅ RT Notifications
✅ Email service
⏳ Search engine
⬜ File upload

Sprints: ✅✅⏳⬜⬜⬜
DoD: 38/78 ✅ | Blockers: 0
```

---

## 9. Risk Assessment

### 9.1 High Risk

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| **Cross-sprint regression** — Sprint 3 breaks Sprint 1's code | High — silent regression, discovered late | Medium | Integration eval catches this. Also: run full test suite after each sprint (not just sprint-specific tests). |
| **Sprint boundary is wrong** — Feature 8 actually depends on Feature 7 but they're in different sprints | High — Sprint 3 blocks on missing prerequisite | Medium | Planner must do proper dependency analysis. If discovered mid-sprint, the orchestrator should pull the missing feature into the current sprint or escalate. |
| **Total elapsed time exceeds agent session limits** — 8 hours across sprints might exceed OpenClaw session limits | High — run crashes mid-project | Low | Sprint results persist to disk. A new session can resume from the last completed sprint. The plugin's state files are the recovery mechanism. |

### 9.2 Medium Risk

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| **Sprint planning overhead** — Time spent extracting/managing sprint plans | Medium — 5–10 min per sprint transition | High (every sprint) | Automate sprint plan extraction. The orchestrator does it as a text operation, not a subagent call. Budget ~2 min per transition. |
| **Owner wants to re-prioritize between sprints** — Feature 15 becomes urgent after Sprint 2 | Medium — requires re-planning remaining sprints | Medium | Natural pause point between sprints. The orchestrator should check for owner input. `harness_checkpoint` with sprint completion is the signal. |
| **Generator in Sprint N makes wrong assumptions about Sprint 1's code** — Summary was too brief | Medium — incompatible code, requires rework | Medium | The guided reading list (§5.2) mitigates this. Generator can read the actual files. If the summary says "Auth middleware in `src/middleware/auth.ts`", the generator reads it. |

### 9.3 Low Risk

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| **Integration eval finds too many issues** — Cross-sprint problems pile up | High but rare | Low | The integration eval is a targeted fix cycle, not a full rebuild. Also: running all tests after each sprint limits drift. |
| **Planner produces bad sprint grouping** — All hard features in one sprint | Medium | Low | The skill prompt should include grouping guidelines. The orchestrator can reject sprints with >7 features. |
| **Backward compatibility of plugin** — Existing non-sprint runs break | Low — data loss | Very Low | All new fields are optional. `sprintMode` defaults to `false`. Existing code paths are unchanged when `sprintMode` is false. |

---

## 10. Final Recommendation & MVP

### 10.1 Is This Worth Implementing?

**Yes, strongly.** The current system has a practical ceiling at ~8 features. The owner's projects (Company OS, multi-agent systems) regularly exceed this. Without sprints, large projects either get split manually by the owner (tedious) or run as monoliths with quality degradation (wastes time on retries).

The sprint system directly addresses all four original problems:
1. **Token overhead** → Each sprint has 3–10x less input than monolithic
2. **Subagent context limits** → Generator focuses on 3–5 features, not 20
3. **Quality** → Smaller scope = deeper implementation, fewer stubs
4. **Incremental delivery** → If Sprint 4 fails, Sprints 1–3 are still delivered

### 10.2 MVP Scope (What to Build First)

**MVP: Orchestrator-level sprints (skill changes only, minimal plugin changes).**

The MVP does NOT require plugin changes. The orchestrator (main agent, guided by the skill) can implement sprints entirely at the skill level:

#### MVP Components

1. **Planner skill prompt update** — Add sprint section to planner system prompt:
   - "If the plan has >8 features, group them into sprints of 3–5 features each"
   - "Output sprint assignments in the plan"
   - Sprint grouping guidelines (dependency-first, domain-cohesion)

2. **Orchestrator sprint loop** — Update SKILL.md workflow:
   - After planner, check if plan has sprints
   - If yes, loop: extract sprint plan → BUILD → CHALLENGE → EVAL → next sprint
   - Between sprints, update master plan with completion markers
   - After all sprints, run integration eval (if >2 sprints)

3. **Sprint plan extraction** — The orchestrator (main agent) extracts sprint-scoped plans:
   - Reads master plan
   - Writes `sprint-N-plan.md` with only that sprint's features + prior sprint summary
   - Passes sprint plan to generator/adversary/evaluator (not master plan)

4. **Progress bar sprint indicator** — Simple addition to `renderProgressBar`:
   - Add `Sprint N/M` header
   - Add sprint status line: `✅✅⏳⬜`
   - Show only current sprint's features

5. **harness_checkpoint sprint tag** — Add optional `sprint` parameter to checkpoint:
   - Backward compatible (undefined = single sprint)
   - Used for progress tracking and recovery

#### What the MVP Does NOT Include

- `harness_sprint_complete` tool (use `harness_checkpoint` with a sprint completion summary instead)
- Sprint-scoped `harness_reset` (reset always resets the whole run)
- Sprint-scoped `harness_submit` validation (submit validates the master plan at the end)
- Automatic sprint plan extraction in the plugin (orchestrator does it manually)
- Sprint state in `run-state.json` (track sprints via checkpoints instead)

#### MVP Effort Estimate

| Component | Effort | Type |
|---|---|---|
| Planner prompt update | 30 min | Skill (prompt edit) |
| SKILL.md sprint orchestration section | 1 hour | Skill (prompt edit) |
| Plan template with sprint section | 30 min | Skill (template edit) |
| Progress bar sprint rendering | 1 hour | Plugin (code) |
| Checkpoint sprint parameter | 30 min | Plugin (code) |
| **Total MVP** | **~3.5 hours** | |

#### Post-MVP (V2)

After the MVP proves the concept:

1. **Plugin state extension** — Add `sprintMode`, `sprintResults` to `RunState`
2. **`harness_sprint_complete` tool** — Formal sprint completion with summary + key files
3. **Sprint-scoped `harness_reset`** — Reset current sprint only
4. **Sprint-scoped `harness_submit`** — Validate per-sprint (allow partial delivery)
5. **Automatic sprint extraction** — Plugin extracts sprint plans from master plan
6. **Sprint re-planning** — Between sprints, optionally re-run planner for remaining sprints
7. **Cross-sprint test enforcement** — After each sprint, run full test suite (not just sprint tests)

### 10.3 Implementation Order

```
MVP Phase 1: Skill-level sprints (prompt changes only)
├── 1. Update planner prompt (sprint grouping)
├── 2. Update plan template (sprint sections)
├── 3. Update SKILL.md (sprint orchestration loop)
└── 4. Update progress bar (sprint indicator)

MVP Phase 2: Plugin support
├── 5. Add sprint parameter to harness_checkpoint
└── 6. Sprint-aware progress bar rendering

V2: Full sprint support
├── 7. RunState extension
├── 8. harness_sprint_complete tool
├── 9. Sprint-scoped reset
├── 10. Sprint-scoped submit
└── 11. Automatic sprint plan extraction
```

### 10.4 Success Criteria

The sprint system is successful if:
- [ ] A 20-feature project completes with all DoD items passing (currently unlikely without sprints)
- [ ] Generator subagent produces zero stubs/TODOs (currently common in large projects)
- [ ] No sprint's generator input exceeds 5,000 tokens (vs ~15,000 monolithic)
- [ ] The owner can see sprint-level progress in Telegram
- [ ] A crashed run can be resumed from the last completed sprint
- [ ] Existing small projects (≤8 features) work exactly as before (backward compatible)

---

## Appendix A: Master Plan Template with Sprints

```markdown
# Plan: [Title]

## Status: READY

## User Request (verbatim)
[...]

## Extracted Requirements
1. [...]
2. [...]

## Context
[...]

## Sprint Overview

| Sprint | Name | Features | Est. DoD Items |
|---|---|---|---|
| 1 | Foundation | Features 1–3 | 12 |
| 2 | Core CRUD | Features 4–7 | 16 |
| 3 | Services | Features 8–11 | 16 |
| 4 | Platform | Features 12–15 | 14 |

## Sprint 1: Foundation

### Feature 1: [Name]
- **Description:** [...]
- **Covers requirements:** #1, #2
- **DoD:**
  - [ ] [criterion]
  - [ ] [criterion]
- **Dependencies:** None

### Feature 2: [Name]
[...]

## Sprint 2: Core CRUD

### Feature 4: [Name]
[...]

## Requirements Coverage Matrix
[unchanged — covers all features across all sprints]

## Technical Notes
[...]

## Out of Scope
[...]
```

## Appendix B: Sprint Context Briefing Template

Passed to generator at the start of Sprint N (N > 1):

```markdown
## Prior Sprints Summary

### Sprint 1: Foundation ✅ (completed, 1 round)
Built: [2-3 sentence summary]
Key files: [list of 3-5 most important files]

### Sprint 2: Core CRUD ✅ (completed, 2 rounds)
Built: [2-3 sentence summary]
Key files: [list]

## Current Sprint: Sprint 3 — Services

[full sprint-3-plan.md content follows]
```

## Appendix C: Decision Matrix — Splitting vs Not Splitting

For the planner to use when deciding:

```
Features ≤ 4 AND DoD items ≤ 15  → NO SPLIT
Features ≤ 8 AND DoD items ≤ 25  → SPLIT OPTIONAL (recommend if features are complex)
Features > 8 OR DoD items > 25   → MUST SPLIT
Features > 15 OR DoD items > 50  → MUST SPLIT, max 5 features per sprint
```

---

*End of analysis. This document is a reference for implementation — no code was written or modified.*
