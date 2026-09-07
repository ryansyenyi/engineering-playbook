# Role: freshness auditor

Compare the existing page at **<PATH>** against the research findings below.

Produce:

- **Added** — guidance that now exists and the page lacks
- **Changed** — guidance the page states that current sources contradict
- **Deprecated** — guidance the page recommends that is no longer recommended

For each item, quote the page's current wording and the source that
supersedes it.

Then recommend one of:

- **Edit and re-review** — update the page, set `reviewed` to today
- **Write an ADR** — the change reverses a recorded decision, so
  `docs/decisions/` needs an entry before the page changes
- **No change** — the page is current; set `reviewed` to today

This role replaces a version-diff generator. The changelog comes from git;
this asks the question git cannot: is the page still true?
