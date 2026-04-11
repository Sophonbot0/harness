# Plan: Add Adversarial Grounding Agent to Harness

## Context
The harness skill at `~/.openclaw/skills/harness/` implements a 3-agent pipeline: Planner → Generator → Evaluator. It works well but suffers from overconfidence — the Generator can produce work that "looks right" but has untested assumptions, and the Evaluator only checks DoD criteria mechanically. There's no agent that actively challenges assumptions and demands evidence.

Inspired by Anthropic's "Building effective agents" (ground truth at each step) and "Demystifying evals for AI agents" (adversarial stress-testing).

## Scope
1. Create adversary system prompt
2. Create challenge report template
3. Update SKILL.md with new 4-agent architecture
4. Update evaluator to consume adversary output

## Feature 1: Adversary System Prompt
- **Description:** Create `prompts/adversary-system.md` — the system prompt for the adversarial grounding agent. This agent runs AFTER the Generator (pre-Evaluator) and challenges the implementation. It does NOT fix — it only finds holes, ranks them, and demands evidence.
- **DoD:**
  - [ ] File `prompts/adversary-system.md` exists
  - [ ] Prompt defines role as "devil's advocate" / adversarial grounding
  - [ ] Prompt instructs to read plan.md + git diff + run code to find evidence
  - [ ] Prompt requires ranking issues by likelihood × impact (not just listing)
  - [ ] Prompt explicitly forbids fixing code — adversary only identifies and challenges
  - [ ] Prompt requires concrete evidence (run tests, check edge cases, try to break things)
  - [ ] Prompt defines output format: challenge-report.md
  - [ ] Prompt includes categories: overconfidence, untested assumptions, missing edge cases, happy-path bias, scope gaps
- **Dependencies:** None

## Feature 2: Challenge Report Template
- **Description:** Create `templates/challenge-report-template.md` — structured format for adversary output.
- **DoD:**
  - [ ] File `templates/challenge-report-template.md` exists
  - [ ] Template includes: Overall Confidence Assessment (with rating 1-5)
  - [ ] Template includes: per-feature challenge section with issues ranked by severity
  - [ ] Template includes: "Demands for Evidence" section — specific tests/checks the Evaluator MUST run
  - [ ] Template includes: "Weakest Points" section — top 3 areas most likely to fail
  - [ ] Template includes: "Overconfidence Flags" — where the Generator claimed success without proof
- **Dependencies:** Feature 1

## Feature 3: Update SKILL.md
- **Description:** Update the main skill definition to reflect 4-agent architecture: Planner → Generator → Adversary → Evaluator. Update workflow, timeouts, loop control.
- **DoD:**
  - [ ] SKILL.md describes 4-agent architecture (Planner → Generator → Adversary → Evaluator)
  - [ ] Quick workflow section updated with Adversary phase
  - [ ] New "Phase 3: ADVERSARY" section with input/output/model specs
  - [ ] Phases renumbered: Plan(1) → Build(2) → Challenge(3) → Eval(4)
  - [ ] Timeout for adversary defined (15 min suggested)
  - [ ] Loop control updated: if Evaluator FAILs, Generator gets BOTH eval-report.md AND challenge-report.md
  - [ ] Model recommendation: adversary should use a different model than generator to avoid same-model blind spots
- **Dependencies:** Features 1, 2

## Feature 4: Update Evaluator Prompt
- **Description:** Update `prompts/evaluator-system.md` to consume the adversary's challenge-report.md. The evaluator should prioritize testing the adversary's "Demands for Evidence" and "Weakest Points".
- **DoD:**
  - [ ] Evaluator prompt references challenge-report.md as input
  - [ ] Evaluator must address each "Demand for Evidence" from the adversary
  - [ ] Evaluator must specifically test each "Weakest Point" identified
  - [ ] Evaluator eval-report.md includes a section: "Adversary Challenges Addressed"
  - [ ] If adversary flagged overconfidence, evaluator must provide concrete evidence (not just "looks ok")
- **Dependencies:** Features 1, 2

## Technical Notes
- The adversary should use a DIFFERENT model family than the generator to avoid correlated blind spots (e.g., if generator is opus, adversary could be gemini or gpt)
- The adversary does NOT have write access to code — read-only + execute tests
- Keep the adversary focused: max 15 min, max 10 challenges ranked by impact
- The adversary's value is in FINDING problems, not solving them

## Out of Scope
- Post-plan adversary (challenge the plan before generation) — future improvement
- Adversary training/fine-tuning
- Multi-round adversary (adversary only runs once per loop)
