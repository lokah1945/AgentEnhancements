# SDD ledger — plan: docs/superpowers/plans/2026-11-16-complete-agent-enhancements-fix.md

BASE: ece38b02

## Pre-flight Review
- Plan covers 8 tasks addressing all critical/high/medium issues from deep E2E audit
- Tasks 1, 2, 3, 4, 6, 7 are independent (different files)
- Task 5 is minor compatibility (registry.py)
- Task 8 depends on all previous
- All commits to master directly
- Spec: Deep E2E audit findings (this conversation)

## Task Status

- [ ] Task 1: Install Runtime Hooks for All Agents
- [ ] Task 2: Link Native Skills for All Agents
- [ ] Task 3: Fix Memory System (Empty memory_type Entries)
- [ ] Task 4: Build Headroom Binary and Improve Fallback Compression
- [ ] Task 5: Fix Registry Structure Compatibility
- [ ] Task 6: Update Setup.sh to Install for All Agents
- [ ] Task 7: Verify Skill Discovery Precision (Configurable max_results)
- [ ] Task 8: Final E2E Verification