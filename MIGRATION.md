# Encyclopedia Migration

Transferring the rhetoric reference collection from the source Fern site
(`us-fda.docs.buildwithfern.com`) to this site — restructured, reformatted,
and rewritten in contemporary academic English.

## Source inventory

- **271 records** in the source index (`/llms.txt`), letters A–Y.
- **2 excluded** — not real content (the API landing page and a typesetting
  artifact, "This page intentionally left blank").
- **43 flagged `needs_review`** — broken artifacts of the source export:
  titles split mid-word ("URES OF SPEECH"), entries spliced together
  ("CICERO; DIALOGICS; PLATO; TOPICS"), body text captured as a second entry,
  and bare contributor names standing in as titles. These are held out of the
  sidebar until repaired. See `migration/manifest.json` for per-entry notes.
- **222 pending** — inventoried, stubbed, and queued for rewriting.
- **4 done** — fully migrated exemplars: Accumulatio, Anaphora, Antithesis,
  Aytoun.

## Pipeline

All tooling lives in `scripts/migration.py` (stdlib only):

| Command | Purpose |
|---|---|
| `python3 scripts/migration.py status` | Progress against the manifest. |
| `python3 scripts/migration.py scaffold` | Create stub pages for pending entries (use `--include-review` to force broken ones, `--force` to overwrite). |
| `python3 scripts/migration.py nav` | Regenerate the `encyclopedia` tab of `fern/docs.yml` from the manifest. Never hand-edit the encyclopedia nav — edit the manifest and regenerate. |
| `python3 scripts/migration.py ingest FILE SLUG` | Clean a fetched raw entry: strips the API wrapper, rejoins hyphen-broken words, restores missing spaces, reflows hard-wrapped lines, splits off bibliography and contributor signature. Writes working text to `migration/raw/clean/` (git-ignored) and metadata to `migration/entries/`. |

### Per-entry workflow

1. Save the entry's `.md` version (append `.md` to the source URL) into
   `migration/raw/<slug>.md`.
2. `python3 scripts/migration.py ingest migration/raw/<slug>.md <slug>`
3. Rewrite the cleaned text to the editorial standard below and replace the
   stub at `fern/docs/pages/encyclopedia/<letter>/<slug>.mdx`.
4. Set `"status": "done"` in `migration/manifest.json`.
5. `python3 scripts/migration.py nav` to refresh the sidebar.

## Editorial standard

Every entry page follows the same template:

1. **Frontmatter** — `title` (dates and epithets move to `subtitle`).
2. **`<Lead>`** — a one-paragraph definition or profile.
3. **Thematic `##` sections** — no unbroken walls of text.
4. **Quotations** — short primary-source quotations only, as blockquotes with
   citations.
5. **Callouts** — `<Note>`, `<Info>`, `<Warning>` for data gaps and reader
   guidance.
6. **Sources** — normalized bibliography.
7. **Provenance** — an `<Accordion>` crediting the original contributor.

Rewrite rules: contemporary professional English; sentences restructured, not
copied; cross-references as internal links (`/a/accumulatio`); original
contributors always credited.

## Before publishing

- Confirm redistribution/adaptation rights for the source material with the
  rights holder; keep contributor attributions intact on every page.
- Re-verify transcribed slugs against the live index during ingest; a few are
  marked `slug_unverified` in the manifest.
- Run `fern check` in CI before merging batches.
