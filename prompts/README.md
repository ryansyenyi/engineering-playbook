# Authoring prompts

Four roles, run by hand, in this order for a new page:

1. `research-agent.md` — gather sources
2. `documentation-writer.md` — turn research into a page
3. `architecture-reviewer.md` — when checking an implementation, not a page
4. `freshness-auditor.md` — when a page enters the research queue

The research queue at `docs/research-queue.md` tells you which pages are due.
A page is due when its status is `stub`, or when `reviewed + review_interval`
has passed.

Promote a role to a Claude Code skill only after it has earned it across
several modules.
