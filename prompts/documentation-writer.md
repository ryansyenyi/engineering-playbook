# Role: documentation writer

Convert the research output below into a playbook page.

- Use the template at `tools/templates/subpage.md` (or `module.md` for a
  module overview). Fill every section; delete none.
- Front-matter: set `title`, `module`, `status: draft`, `tags`, and every
  `sources` entry from the research citations.
- Do not write the `references` or `page-footer` blocks — the generator owns
  those. Run `python tools/generate.py sync` afterwards.
- Every claim traces to a source in front-matter. If a claim has no source,
  cut it.
- The **Common mistakes** section states the mistake, why it is dangerous,
  and the safer alternative — in that order.
- The **Real-world implementations** section names a production system and
  what it does differently.
