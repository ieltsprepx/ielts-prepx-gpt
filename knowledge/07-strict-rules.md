# 07 — Strict Rules & Common Pitfalls

This document consolidates every non-obvious rule, historical mistake, and edge-case that the GPT must enforce. Read this for every generation, conversion, or validation task.

> Bullets that duplicate a rule already caught automatically by `QEditorReplaceBodySchema`/`validate_part.py` (e.g. blank-count/position matching, options-array length) were trimmed — see `01-schema-entities.md` for those. This doc keeps the rules the validator can't catch for you: heuristics, conventions, and historical mistakes.

---

## Artifact Structure

- Part file = `{ "passages": [], "sections": [], "questions": [] }` only.
- Never wrap in `{ "part": ..., "progress": ..., "nextAction": ... }`.
- Never print the full JSON into chat unless the user explicitly asks.
- Never claim a file exists unless it was actually created and passed validation.

## Sections

- `sections[].description` is a **rich-text HTML string** (Tiptap-serialized), never plain text — wrap instructions in `<p>` tags, use `<br>` for line breaks. Allowed tags: `p, br, strong, em, u, s, h2–h4, ul, ol, li, table` family, `code`, `pre`. No scripts/styles/iframes/images.
- `null` is valid when there are no instructions.
- Feature lists (`matching_features`) and word-limit sentences live in the description HTML — see `01-schema-entities.md` for the full format contract.

## Passages

- `passages[].content` is an **HTML string** (Tiptap-serialized). Use `<p>` tags for paragraphs.
- For `matching_heading` sections, the HTML must include `<div data-type="heading-drop" data-question-id="<uuid>"></div>` blocks — one per item, placed **immediately before (on top of) the paragraph it belongs to**, never after it.
- `references[].text` must be a **verbatim substring** of the passage HTML (rendering re-finds highlights by searching this text). `from`/`to` are best-effort — 0/0 defaults are acceptable if `text` is accurate.

## Questions

- Every `questionId` must be a valid UUID v4, unique across the **entire set** — not just the part.
- `answerType` must match the presentation type per the mapping in `01-schema-entities.md`.
- `correctAnswer` is always an array of strings with at least one element.

## Choice Questions (single_choice, multiple_choice)

- `correctAnswer` = **option letters**, not option text. First option = A, second = B, etc.
- Single choice: exactly one letter. Multiple choice: two or more letters.

## Select From List

- `correctAnswer` = letters from the shared options pool.
- `answerType` = `multiple_choice` (assigned by the editor's select-from-list builder; matches production exports).

## Statement Types (true_false_not_given, yes_no_not_given)

- `correctAnswer` = `["TRUE"]` / `["FALSE"]` / `["NOT GIVEN"]` (or `["YES"]` / `["NO"]` for yes/no variants).

## Completion Types (note, summary, sentence, table, form)

- `presentationConfig.content` must be a native Tiptap `{"type":"doc","content":[...]}` — **never HTML**, never an object with an `html` field.
- Blank nodes: exactly `{"type":"blank","attrs":{"questionId":"<uuid>"}}`. Inline atom nodes.
- `items` contains `{ "questionId": "<uuid>" }` only — no `questionText` (text lives in the Tiptap template).
- Grid types use Tiptap table structure: `doc → table → tableRow → tableCell/tableHeader → paragraph → blank`.
- **Empty text nodes are forbidden.** Never emit `{"type":"text","text":""}` anywhere in Tiptap content — the editor rejects the whole document and renders it empty. An empty line/cell = a `paragraph` with no `content` array.
- **Do not add speculative attrs.** When a table/completion fails to render, do not add `colspan`/`rowspan`/`colwidth`/`textAlign` attrs (or remove `tableHeader`, or move nodes) as a guess. Check for empty text nodes first; that is the cause in nearly every case.
- WordBank: omit entirely if no word bank. Never emit `{ "words": [], ... }`.
- **Option-box completions** (PDF shows a boxed A–P option list): `wordBank.words` = letters, `correctAnswer` = letters, letter→word mapping table in section `description`. See `02-presentation-types.md` Family 3.

## Matching Types

- `wordBank` is **required** for all matching types — not optional.
- **Reuse derivation**: if the PDF instruction says "You may use any letter/option more than once" (or "NB You may use…"), then `wordBank.reuse` MUST be `true`. Otherwise default `false`. Never leave `reuse: false` on a section whose description says "more than once".
- `matching_features`: `wordBank.words` = label letters `["A","B","C","D","E"]`. Feature descriptions go in section `description`, NOT in wordBank. `correctAnswer` = letter.
- `matching_information`: same letter pattern — `wordBank.words` = paragraph letters, `correctAnswer` = letter.
- `matching_sentence_end`: `wordBank.words` = sentence endings, `correctAnswer` = ending text.
- **`matching_heading` is special**: `wordBank.words` = **plain heading texts** (no roman numeral prefixes — the renderer auto-numbers them i, ii, iii…). `correctAnswer` = exact heading text from wordBank. `items[].questionText` = the **paragraph letter only** (`"A"`, `"B"`, …) — never a description. Each item needs exactly one `<div data-type="heading-drop" data-question-id="<uuid>">` in the passage HTML, placed immediately before its paragraph. Reuse is typically `false`.
- Tabular variants are identical in schema, rendered as two-column tables.

## Visual Types (diagram, flow_chart, map_plan, diagram_labeling)

- `assetId` is required. Use placeholder like `"TODO-upload-map-p1"` when no image.
- `markerLayout`: `"on_image"`/`"below_image"` → items require `position {x, y}` (0–100). `"question_list"` → items require `questionText`, `position` forbidden.

## Speaking Types

- `speaking_cue_card` requires `topic`, `bulletPoints`, `prepTimeSeconds`, `speakingTimeSeconds`.

## Validation Object

- **Required on every question.** Always include the `validation` object, even when empty (`{}`).
- Only these keys allowed: `maxWords`, `minWords`, `caseSensitive`, `acceptedAnswers`. No other keys.

## Listening Transcripts

- Deliver as separate `.txt` file in the format defined in `06-listening-transcript.md`.
- Also deliver the question set part as a separate `.json` file.
- `passages[0].content` contains the transcript text (without format directives).

## PDF Conversion

- Preserve source content and terminology exactly. Do not replace with general knowledge.
- If no answer key, ask once. If AI-populated, disclose in chat.

## Answer Keys (general)

- Every question must have a defensible `correctAnswer`.
- For open-ended text answers, add reasonable alternatives in `validation.acceptedAnswers`.
- Choice `correctAnswer` is always letters, never option text.
- Matching `correctAnswer` is letters for features/information, text for headings/sentence-ends.

## Historical Mistakes (do not repeat)

- Printing raw JSON into chat instead of delivering as file.
- Wrapping part artifacts in `{ part, progress, nextAction }` envelopes.
- Claiming a file was generated without evidence in the conversation.
- Including roman numeral prefixes in matching_heading wordBank words.
- Using `single_choice` or `text` answerType for `select_from_list` questions (must be `multiple_choice`).
- **Empty text nodes in Tiptap tables/content** (`{"text":""}`) — editor renders the whole section empty. Most frequent listening-conversion failure; check this FIRST whenever a table does not render.
- **Speculative serialization changes** — adding table/paragraph attrs, removing `tableHeader`, or restructuring a valid-looking doc while guessing at an editor bug. Diagnose (empty text nodes) before changing structure.
- **Reusing a filename when regenerating a file** — the platform re-serves the cached old artifact, so the user downloads the stale version. Every regeneration gets a NEW versioned filename (`-v2`, `-v3`, …).
- **Filling missing PDF pages from the web or placeholders** — never source passage/question text from external websites, and never emit `"Option A"`/`"Option B"` placeholder text. Ask the user for the complete PDF.
- **Misclassifying presentation types** — the recurring confusions: shared-option/dropdown boxes are `select_from_list` (not `multiple_choice`); "classify… you may use any letter more than once" is `matching_features`; blanks inside a grid/table are `table_completion`; Q&A with a boxed A–P option list is a completion with letter wordBank + mapping description. Use the decision table in `04-pdf-to-json.md`.
- **Flattening PDF layouts** — forms/tables in the PDF must become Tiptap table structures in the JSON; do not collapse them into plain sentence lines. Mirror the PDF's question-range blocks (e.g. "Questions 1–5" and "Questions 6–10" stay separate sections).
- **Setting `reuse: false` when the description says "more than once."**
- **Mixing letters and full text** in wordBank/correctAnswer for the same section — pick ONE representation and keep description, wordBank, and answers internally consistent.
