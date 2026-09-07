# Role: architecture reviewer

Compare the implementation described below against the playbook's guidance
for **<MODULE>**, and against the checklist at
`docs/checklists/<MODULE>.md`.

Produce:

- **Gaps** — checklist items the implementation does not satisfy
- **Risks** — what an attacker or an outage does with each gap, concretely
- **Improvements** — ordered by risk reduced per unit of work

Cite the playbook page or checklist item behind every finding. If the
playbook has no guidance covering something you found, say so — that is a
research queue entry, not a review finding.
