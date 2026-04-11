# Plan: Long-Running Task Quality Enforcement

## Context

The harness skill (Planner → Generator → Adversary → Evaluator) is prompt-level only. The agent can ignore it, skip phases, claim "done" without verification, and degrade as context fills up. Subagents fail silently. There's no runtime enforcement.

After reading the OpenClaw plugin SDK (`types.d.ts`, `runtime/types.d.ts`), the following runtime primitives are confirmed available:

| Primitive | What it gives us |
|---|---|
| `api.on("llm_output", ...)` | Inspect every LLM response — token usage, content |
| `api.on("agent_end", ...)` | Know when an agent run finishes, success/failure, duration |
| `api.on("subagent_spawned", ...)` | Track subagent lifecycle |
| `api.on("subagent_ended", ...)` | Detect subagent failures, timeouts, outcomes |
| `api.on("before_prompt_build", ...)` | Inject context (progress state, warnings) into prompts |
| `api.on("before_tool_call", ...)` | Block or modify tool calls |
| `api.on("after_tool_call", ...)` | Validate tool results |
| `api.on("before_compaction", ...)` | Intercept context compaction, save state |
| `api.on("after_compaction", ...)` | Restore state after compaction |
| `api.on("session_start/end", ...)` | Session lifecycle tracking |
| `api.registerTool(...)` | Provide tools to the agent (checkpoint, progress report) |
| `api.registerService(...)` | Background watchdog service |
| `api.registerHttpRoute(...)` | Status dashboard / API |
| `api.registerCommand(...)` | Owner commands (`/harness-status`, `/harness-abort`) |
| `api.runtime.subagent.run(...)` | Spawn subagents programmatically |
| `api.runtime.subagent.waitForRun(...)` | Wait for subagent completion with timeout |
| `api.runtime.subagent.getSessionMessages(...)` | Read subagent output |
| `api.runtime.subagent.deleteSession(...)` | Clean up |

**Key limitation:** There is NO hook to intercept/reject the agent's final response before delivery. `llm_output` is observational. `message_sending` can cancel outbound messages but only on channel-bound conversations. There is no `before_agent_response_accept` gate.

**Key limitation:** There is no `context_window_usage` event. We can track token usage via `llm_output.usage` but cannot directly query "how full is the context window right now."

## Analysis of Options

### Option A: Pure Plugin — ❌ Not Sufficient Alone
Plugins can monitor and spawn subagents, but cannot orchestrate the 4-agent pipeline autonomously. The pipeline requires the main agent to interpret results, make decisions, and communicate with the user. A plugin without any skill guidance would need to fully replace the agent's decision loop, which the hook API doesn't support (no response interception/rejection).

### Option B: Enhanced Skill — ❌ Doesn't Solve Core Problems
Better prompts don't prevent: silent subagent failures, context window degradation, quality gate bypass. The agent can still ignore everything. This is what we already have.

### Option C: Hybrid (Plugin + Skill) — ✅ RECOMMENDED
The plugin handles what prompts can't enforce: failure detection, retry logic, progress persistence, metrics, watchdog monitoring. The skill handles what plugins can't do: guide the agent's reasoning, pipeline orchestration decisions, user communication.

### Option D: Context Engine Plugin — ❌ Overscoped
A custom context engine would replace LCM (lossless-claw), which already works well. The problems aren't about context compaction quality — they're about task progress surviving compaction and quality enforcement. This is better handled by hooks on the existing context engine events (`before_compaction`, `after_compaction`).

## Recommendation: Option C — Hybrid Plugin + Skill

**Plugin name:** `harness-enforcer`  
**Plugin location:** `~/.openclaw/extensions/harness-enforcer/`

The plugin is the "immune system." The skill is the "brain." The plugin can't be ignored; the skill can be.

---

## Scope

1. **Feature 1:** Subagent Lifecycle Guardian
2. **Feature 2:** Progress Persistence & Context Rotation
3. **Feature 3:** Quality Gate Enforcement
4. **Feature 4:** Watchdog Service
5. **Feature 5:** Owner Visibility (Commands + HTTP)
6. **Feature 6:** Enhanced Harness Skill (updated prompts)

---

## Feature 1: Subagent Lifecycle Guardian

**Description:** Plugin hooks into `subagent_spawned` and `subagent_ended` to track all harness subagents. Detects failures (outcome: error/timeout/killed), empty outputs, and 6-second ghost responses. Automatically retries failed subagents up to 2 times with exponential backoff. Logs all lifecycle events.

- DoD:
  - [ ] `subagent_spawned` hook registers every harness subagent (identified by session key pattern `agent:*:subagent:harness-*`) with spawn time, phase, and run ID
  - [ ] `subagent_ended` hook detects failure outcomes (`error`, `timeout`, `killed`) and triggers retry via `api.runtime.subagent.run()`
  - [ ] After subagent ends, `getSessionMessages()` is called to check for empty/minimal output (< 50 chars of assistant content). If detected, logs warning and triggers retry
  - [ ] Retry budget: max 2 retries per phase per round, with 5s/15s backoff delays
  - [ ] All lifecycle events written to `~/.openclaw/harness-enforcer/runs/{runId}/lifecycle.jsonl`
  - [ ] Retries use a fresh session key (appending `-retry-{n}`) to get clean context
- Dependencies: None

## Feature 2: Progress Persistence & Context Rotation

**Description:** Plugin provides a `harness_checkpoint` tool that the agent calls to save task progress. Hooks into `before_compaction` and `after_compaction` to preserve progress state across LCM compaction. On `before_prompt_build`, injects the latest checkpoint summary into the agent's context so it knows where it left off.

- DoD:
  - [ ] `harness_checkpoint` tool registered, accepting: `{ phase, round, completedFeatures, pendingFeatures, blockers, summary }`
  - [ ] Checkpoint data written to `~/.openclaw/harness-enforcer/runs/{runId}/checkpoint.json`
  - [ ] `before_compaction` hook saves current checkpoint + copies of plan.md, eval-report.md, challenge-report.md paths to the run directory
  - [ ] `before_prompt_build` hook injects checkpoint summary (< 500 tokens) as `prependContext` when a harness run is active
  - [ ] Checkpoint includes: elapsed time, rounds completed, features done/pending, last phase completed, last failure reason
  - [ ] Agent can call `harness_checkpoint` at any point; plugin validates required fields
  - [ ] If context exceeds 70% usage (estimated from `llm_output.usage` history), the injected context includes a warning: "Context is filling up. Checkpoint progress and consider delegating remaining work to subagents."
- Dependencies: None

## Feature 3: Quality Gate Enforcement

**Description:** Plugin provides a `harness_submit` tool that the agent MUST call to deliver results. This tool validates that: (a) an eval-report.md exists, (b) the eval grade is PASS, (c) all DoD items in plan.md are checked. If validation fails, the tool returns an error with the specific gaps, forcing the agent to address them before delivery.

- DoD:
  - [ ] `harness_submit` tool registered, accepting: `{ planPath, evalReportPath, challengeReportPath }`
  - [ ] Tool reads `eval-report.md` and parses grade (PASS/FAIL). If FAIL or missing, returns error: "Cannot submit: evaluation grade is FAIL/missing"
  - [ ] Tool reads `plan.md` and counts unchecked DoD items (`- [ ]` vs `- [x]`). If any unchecked, returns error listing them
  - [ ] Tool reads `challenge-report.md` and checks for unaddressed CRITICAL issues. If any, returns error
  - [ ] On successful validation, tool writes `~/.openclaw/harness-enforcer/runs/{runId}/delivery.json` with timestamp, grade, metrics
  - [ ] The `before_prompt_build` hook reminds the agent: "You MUST call harness_submit to deliver results. Direct delivery without harness_submit is not verified."
  - [ ] Metrics tracked: total rounds, time per phase, adversary catch rate, retry count
- Dependencies: Feature 2 (checkpoint for run tracking)

## Feature 4: Watchdog Service

**Description:** A background service that monitors active harness runs. Detects: stalled agents (no tool calls for > 10 min), runaway sessions (> 3 hours total), and orphaned subagents.

- DoD:
  - [ ] `api.registerService({ id: "harness-watchdog", ... })` starts a background interval (every 60s)
  - [ ] Watchdog reads active runs from `~/.openclaw/harness-enforcer/runs/` and checks last activity timestamp
  - [ ] If no activity for 10 minutes, writes warning to run log
  - [ ] If total run time exceeds 3 hours, writes alert to run log
  - [ ] Orphaned subagent detection: if a subagent session key is in "spawned" state for > 50 minutes (beyond any phase timeout), logs error
  - [ ] Watchdog state file: `~/.openclaw/harness-enforcer/watchdog-state.json`
- Dependencies: Feature 1 (lifecycle data), Feature 2 (checkpoint data)

## Feature 5: Owner Visibility

**Description:** Slash commands and an HTTP endpoint for the owner to inspect harness run status.

- DoD:
  - [ ] `/harness-status` command returns: active run info (phase, round, elapsed time, features done/pending, retries, last checkpoint)
  - [ ] `/harness-abort` command sets a flag that the `before_prompt_build` hook reads, injecting "The owner has aborted this harness run. Stop all work and report current status."
  - [ ] `api.registerHttpRoute({ path: "/harness/status", ... })` returns JSON with all active and recent runs (last 10)
  - [ ] HTTP route returns: run ID, phase, round, start time, elapsed, grade, retry count, checkpoint summary
- Dependencies: Feature 1, 2, 3

## Feature 6: Enhanced Harness Skill

**Description:** Update the harness skill prompts to work with the plugin. Add checkpoint instructions, harness_submit requirement, and context-awareness guidance.

- DoD:
  - [ ] `SKILL.md` updated to reference harness-enforcer plugin as a dependency
  - [ ] `SKILL.md` workflow updated: step 6 becomes "SUBMIT → call harness_submit tool to deliver verified results"
  - [ ] Generator system prompt updated: must call `harness_checkpoint` after each feature completion
  - [ ] Generator system prompt updated: must call `harness_submit` instead of directly reporting "done"
  - [ ] All phase prompts updated: include awareness that the plugin is monitoring and will retry failures
  - [ ] Planner system prompt updated: must include machine-parseable DoD format (`- [ ]` checkboxes only, one per line, no nested bullets)
- Dependencies: Features 1-5 (plugin must exist first)

---

## Technical Notes

### Plugin Structure
```
harness-enforcer/
├── index.ts              # definePluginEntry, register hooks/tools/service/commands/routes
├── openclaw.plugin.json  # config schema
├── package.json
├── src/
│   ├── lifecycle.ts      # Feature 1: subagent tracking + retry
│   ├── checkpoint.ts     # Feature 2: progress persistence tool + hooks
│   ├── quality-gate.ts   # Feature 3: harness_submit tool + validation
│   ├── watchdog.ts       # Feature 4: background service
│   ├── commands.ts       # Feature 5: /harness-status, /harness-abort
│   ├── http.ts           # Feature 5: HTTP status route
│   └── types.ts          # Shared types
└── tsconfig.json
```

### Identifying Harness Sessions
Session keys for harness subagents should follow the pattern: `agent:main:subagent:harness-{phase}-{runId}` (e.g., `agent:main:subagent:harness-generator-abc123`). The plugin matches on `harness-` prefix in subagent session keys.

### State Storage
All state goes to `~/.openclaw/harness-enforcer/runs/{runId}/`. This is plain JSON files — no database dependency. The watchdog scans this directory.

### Token Usage Tracking
We cannot directly query context window fullness. Instead, we accumulate `llm_output.usage.total` across a session and compare against the model's known context window size (which we'd need to maintain a lookup table for, or estimate conservatively at 128K). This is imperfect but better than nothing.

### What This Does NOT Solve
- **Agent intentionally circumventing the plugin:** The agent could technically avoid calling `harness_submit` and just respond directly. The plugin reminds it via `prependContext` but cannot block direct responses. A `message_sending` hook could cancel outbound messages during active harness runs, but this risks blocking legitimate status updates.
- **Model quality degradation from context pressure:** The plugin can warn about context usage, but the fundamental fix is the model's context handling. LCM already helps here.
- **Cost control:** The retry mechanism increases cost. Should be configurable.

### Configuration (openclaw.plugin.json)
```json
{
  "maxRetries": 2,
  "retryBackoffMs": [5000, 15000],
  "watchdogIntervalMs": 60000,
  "stallTimeoutMs": 600000,
  "maxRunDurationMs": 10800000,
  "contextWarningThreshold": 0.7,
  "enableAutoRetry": true
}
```

## Out of Scope

- Replacing LCM / custom context engine
- Multi-agent orchestration without the main agent (fully autonomous plugin pipeline)
- Cost tracking and billing
- Integration with external CI/CD systems
- Real-time streaming updates to owner (beyond polling /harness/status)
- Cross-run learning (remembering which approaches failed in previous runs)
