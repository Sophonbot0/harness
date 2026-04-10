# Plan: Sprint-Based Planning for Large Projects

## Status: READY

## User Request (verbatim)
"No planner caso o projeto seja complexo de mais não deve haver limite de items, se houverem tipo muito por ser um projeto grande pode partir o projeto por sprints e tratar de um sprint de cada vez mas deve SEMPRE levar tudo do início ao fim"

## Extracted Requirements
1. [Explicit] No limit on features/items — planner covers everything
2. [Explicit] Large projects split into sprints
3. [Explicit] One sprint at a time, each fully completed
4. [Explicit] Always go from start to finish (no partial delivery)
5. [Implicit] Split threshold: >8 features OR >25 DoD items
6. [Implicit] Sprint size: 3-5 features each
7. [Implicit] Each sprint is a full harness cycle (PLAN→BUILD→CHALLENGE→EVAL)
8. [Implicit] Context between sprints: compact briefing, not full history
9. [Implicit] SKILL.md documents the sprint orchestration flow
10. [Implicit] Planner prompt updated to produce sprint-aware plans
11. [Implicit] Plan template updated with sprint structure
12. [Implicit] Progress bar shows sprint-level progress

## Features

### Feature 1: Update Planner Prompt for Sprint-Aware Planning
- **Description:** Planner produces a master plan with ALL features, then groups them into sprints if threshold exceeded.
- **DoD:**
  - [ ] Planner prompt includes sprint splitting instructions
  - [ ] Threshold documented: >8 features OR >25 DoD items triggers sprint mode
  - [ ] Sprint grouping rules: by dependency first, then by domain
  - [ ] Sprint size: 3-5 features per sprint (max 7)
  - [ ] Master plan always covers ALL requirements start to finish
  - [ ] Each sprint has its own feature list with DoD items

### Feature 2: Update Plan Template for Sprints
- **Description:** Plan template supports optional sprint sections.
- **DoD:**
  - [ ] Plan template has optional Sprint sections after Features
  - [ ] Each Sprint section lists which features it covers
  - [ ] Sprint dependency order is explicit
  - [ ] Template works for both sprint and non-sprint plans (backward compatible)

### Feature 3: Update SKILL.md Sprint Orchestration
- **Description:** SKILL.md documents how the orchestrator runs sprints sequentially.
- **DoD:**
  - [ ] SKILL.md has a "Sprint Execution" section
  - [ ] Documents: detect sprint plan → run sprint 1 fully → run sprint 2 → etc.
  - [ ] Context handoff: what the next sprint's generator receives (briefing from prior sprints)
  - [ ] Integration eval after all sprints (if >2 sprints)
  - [ ] Progress bar shows sprint progress (Sprint 2/4 + within-sprint %)

### Feature 4: Update Progress Bar for Sprint Awareness
- **Description:** Progress bar renderer supports sprint-level display.
- **DoD:**
  - [ ] renderProgressBar accepts optional sprintCurrent/sprintTotal params
  - [ ] When in sprint mode, shows: "Sprint 2/4" in the header
  - [ ] Overall progress calculated across all sprints, not just current
  - [ ] Backward compatible: works without sprint params (existing behavior)

## Technical Notes
- MVP is skill-level only — no plugin schema changes needed
- The orchestrator (main agent) handles sprint detection and looping
- Sprint detection: read plan.md, check for `## Sprint N` sections
- Each sprint gets its own BUILD→CHALLENGE→EVAL cycle
- Between sprints, the orchestrator composes a briefing from prior sprint eval reports

## Out of Scope
- Plugin state changes for sprints (V2)
- Cross-sprint dependency resolution at runtime
- Sprint re-ordering or re-prioritization mid-execution
