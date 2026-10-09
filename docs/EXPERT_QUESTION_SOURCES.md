> **Public edition:** Census town points and reviewed reference catalogs are bundled. Optional data collections retain their publishers' original location qualifications. Private find locations and personal data are excluded from Git. See the [README](../README.md) for the data inventory.

﻿# Expert questions and attributed responses

`core.expert_questions` is an authored recording workflow. It makes no new identification, age, probability, credentials, source-verification or collection-rights determination. It contacts nobody. The photo checklist describes the existing observation workflow; no photographs are embedded, stored, transmitted or analyzed by these functions. No new provider or external factual source is introduced.

## API

`prepare_question(row, question, comparison, wanted_detail)` copies a valid saved fieldbook row and appends an explicitly user-authored question, possible interpretation and wanted detail. Question is required; comparison/detail may be empty. Existing original Markdown is preserved exactly as a prefix. Original title, kind, saved timestamp, record ID and all comparison fields are preserved in the new Markdown. Optional broad town context is inherited only from the already-saved row; this API never looks up a place or infers origin from a rock map.

`response_entry(question_row, attribution, response_date, response, remaining_uncertainty)` appends a separately attributed user-recorded response. A prepared expert-question row is required; response-to-response chains are rejected so additional responses can be attached separately to the original question. Attribution and response are required. Date must be a valid calendar `YYYY-MM-DD`. Blank remaining uncertainty means 'Not recorded', not 'none'. The stated response date may predate record creation: it is a user-reported source date, separate from the new entry's server-generated UTC saved timestamp.

Both functions return the unchanged version-1 six-key row shape (`id`, `kind`, `title`, `created`, `summary`, `markdown`) with kind `investigation`. Input rows are never mutated. Content-derived 24-character IDs include parent identity and deduplicate repeated saves. Original summary keys are sorted when preserving them so import key ordering does not alter IDs. Existing `validate_book` and `merge_entries` work without schema changes.

## Existing summary fields

Questions copy original comparison fields, including `place` only when present, and set `mission=Expert question`, `source=Saved observation: <parent id>`, `outcome=Question prepared; no response recorded`, `follow_up=<question>`, `steps=<wanted detail or Not recorded>`.

Responses preserve comparison fields and set `mission=Expert response`, `source=<user attribution>`, `date=<stated response date>`, `outcome=User-recorded response; not independently verified`, `follow_up=<remaining uncertainty or Not recorded>`. Superseded source/date/question fields remain in the preserved Markdown snapshot.

## Input limits and rendering

All form parameters are strict strings. UTF-8 byte limits: question/comparison/wanted detail/remaining uncertainty 1,500; attribution 200; response 4,000; response date 10. Invalid Unicode, control/invisible characters and oversized content raise `ValueError`; LF is allowed for multiline text. Existing fieldbook limits still bound titles, summary fields and complete Markdown to 100,000 bytes. Unicode title truncation preserves valid UTF-8.

New user text is escaped as literal Markdown/HTML. Existing snapshots are preserved, and imported/saved record Markdown must continue to be rendered as literal text using the existing fieldbook reader. The API's attribution is not a verified expert identity; the UI should explicitly label it user-recorded. No messaging, email, upload or provider request is part of these functions.

Tests cover immutable source/order/metadata preservation, optional town absence, valid schema round trips, stable deduplication across repeated saves and key-order changes, attribution/calendar-date validation, Unicode/controls/bounds, escaped hostile markup, incompatible record order, and overall record-size limits.
