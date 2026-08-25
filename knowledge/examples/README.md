# 08 — Reference Examples (Production-Validated Parts)

Nine real part artifacts converted from a platform question-set export (`export-1787638892008.json`, exported 2026-08-25). Every file passes `validate_part.py` with 0 errors. Treat these as **ground truth** for shape, style, and conventions — when a doc rule and an example disagree, the example reflects what production actually stores.

---

## File Index

| File | Skill | Part | Presentation types | Notable features |
|---|---|---|---|---|
| `writing-day-one-part-1.json` | writing | Task 1 | `large_answers` | HTML passage with embedded `<img>`; `minWords: 150` |
| `writing-day-one-part-2.json` | writing | Task 2 | `large_answers` | Essay prompt passage; `minWords: 250` |
| `reading-aphantasia-part-1.json` | reading | Passage 1 | `true_false_not_given`, `sentence_completion` | `orderedList` with `attrs.start: 9`; `hardBreak`; `maxWords: 2` |
| `reading-aphantasia-part-2.json` | reading | Passage 2 | `matching_heading`, `sentence_completion`, `single_choice` | heading-drop divs in passage HTML; `attrs.start: 22`; wordBank = heading texts |
| `reading-aphantasia-part-3.json` | reading | Passage 3 | `true_false_not_given`, `single_choice`, `summary_completion` | table HTML inside section description; summary as one paragraph with `hardBreak`s |
| `listening-tennis-court-part-1.json` | listening | Part 1 | `note_completion` | single paragraph, `hardBreak`-separated bullets, bold note headings, `acceptedAnswers` number alternates |
| `listening-tennis-court-part-2.json` | listening | Part 2 | `select_from_list`, `single_choice`, `map_plan_labeling` | shared options pool; `markerLayout: "question_list"`; letter wordBank A–G; `assetId` |
| `listening-tennis-court-part-3.json` | listening | Part 3 | `matching_features`, `single_choice` | feature list (A–E) lives in section `description` HTML; wordBank = label letters |
| `listening-tennis-court-part-4.json` | listening | Part 4 | `note_completion` | `bulletList` blocks under bold headings; ONE WORD ONLY → `maxWords: 1` |

---

## Export Envelope vs Part Artifact

The source export wraps everything in a whole-set envelope:

```json
{ "version": 1, "exportedAt": "...", "filters": {...}, "questionSets": [ { "code", "title", "skill", "type", "assets", "parts": [...] } ] }
```

The editor accepts **none of that**. Each part file is exactly `{ passages, sections, questions }` (see `01-schema-entities.md`). Conversion applied:

| Export field | Part artifact |
|---|---|
| `questionSets[].parts[].questions[]._id` | `questions[].id` |
| `questions[].order` | **dropped** — server recomputes order by walking sections in order |
| set-level `assets` (listening audio, images) | **dropped** — not representable in a part artifact; uploaded separately |
| `part.title`, `part.order`, set `code`/`title`/`skill`/`type` | **dropped** — envelope metadata, rejected by the editor |
| `passages[].references` (absent in export) | `[]` |

File naming here uses readable slugs for documentation; real deliveries follow `<set-code>-part-<n>.json` (see `03-delivery-protocol.md`).

---

## Patterns to Copy

### Completion content (all 5 completion/grid types)

- Content is always a **native Tiptap doc** — `{"type":"doc","content":[...]}`. Never HTML.
- Blanks are inline atoms: `{"type":"blank","attrs":{"questionId":"<uuid>"}}`. `items[]` mirrors blanks **in document order**, count and IDs identical.
- **Question numbering within a section** uses `orderedList.attrs.start` to continue exam numbering (e.g. a "Questions 9–13" section starts its list at `9`). See `reading-aphantasia-part-1.json`.
- `hardBreak` nodes produce line breaks inside a paragraph; `marks: [{"type":"bold"}]` styles note headings. See `listening-tennis-court-part-1.json` (flat notes) vs `listening-tennis-court-part-4.json` (`bulletList` blocks).
- `sentence_completion`: one `listItem` per sentence, one blank per sentence. `summary_completion`: single flowing paragraph with `hardBreak`s.

### `maxWords` from instruction wording

| Instruction | `validation.maxWords` |
|---|---|
| "ONE WORD ONLY" / "ONLY ONE WORD" | `1` |
| "NO MORE THAN TWO WORDS" | `2` |

Always pair with `caseSensitive: false`.

### Heading-drop serialization (`matching_heading`)

Production passage HTML serializes attribute order as `data-question-id` **before** `data-type`:

```html
<div data-question-id="<uuid>" data-type="heading-drop"></div>
```

Both attribute orders are valid (the validator accepts either). Each item's `questionId` appears exactly once. In production, `items[].questionText` holds the **paragraph letter** ("A"…"H"), and `wordBank.words` holds plain heading texts (no roman prefixes). `correctAnswer` = the exact heading text.

### `select_from_list`

Shared `options` pool at the config level; `items[]` carry only `questionId`. `answerType` is **`multiple_choice`** (this is what the editor assigns and what production stores — see `listening-tennis-court-part-2.json` Questions 11–12), `correctAnswer` = letter(s) from the pool.

### `matching_features`

The A–E feature list lives in the **section `description`** (HTML), not in the config. `wordBank.words` = `["A","B","C","D","E"]`, `reuse: false`, `correctAnswer` = letter.

### `map_plan_labeling` (pre-labeled plan)

`markerLayout: "question_list"` for images with letters baked into the asset: each item has `questionText` (the place to label, e.g. "Gift shop"), **no** `position`, and a letter wordBank (`A`–`G`). `assetId` references a platform-uploaded asset.

### Writing tasks

One `large_answers` section per task, single item ("Write your response below."), `answerType: "text"`, `minWords` = 150 (Task 1) / 250 (Task 2), `correctAnswer` = placeholder text. The prompt (chart + instructions) lives in the passage HTML, including any `<img>`.

### Numeric answers

Store the digit form as `correctAnswer` and accept word alternates: `correctAnswer: ["2"]`, `validation.acceptedAnswers: ["two"]`.

---

## Environment-Specific Values

`assetId`s and `assets.ieltsprepx.app` URLs in these files point at platform storage. **Never copy them into generated output** — use descriptive placeholders (e.g. `"TODO-upload-map-p1"`) and let the editor swap in real assets.
