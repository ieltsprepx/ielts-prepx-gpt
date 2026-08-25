# 01 — Question Set Entity Schema (Single Source of Truth)

This document defines the **editor-replace JSON format** — the exact structure validated by `QEditorReplaceBodySchema` and imported via the Question Editor's JSON dialog (`json-editor-dialog.tsx`). Every artifact (PDF conversion, AI generation) must conform to this shape.

> Derived from: `question-editor-replace.dto.ts` (backend), `editor-form.schema.ts` (frontend)
> **Scope**: Per-part (`PUT /questions/editor/:partId`), NOT the whole-set import envelope.

---

## Top-Level Shape

```json
{
  "passages": [],
  "sections": [],
  "questions": []
}
```

These are the **only three keys** allowed in a part artifact. Do NOT wrap in `{ "part": ..., "progress": ..., "nextAction": ... }`.

---

## `passages[]`

```json
{
  "order": 1,
  "title": "Passage title",
  "content": "<p>HTML paragraph content...</p>",
  "references": []
}
```

| Field | Type | Rules |
|---|---|---|
| `order` | integer (1–100) | Sequential starting at 1, no gaps, no duplicates. |
| `title` | string | Required. |
| `content` | string | Required. **HTML string** — the passage content including paragraph tags. For `matching_heading` sections, the HTML must include heading-drop div blocks (see below). For listening transcripts, this is the plain transcript text (may be prefixed with `[TRANSCRIPT]`). |
| `references` | array | Optional (default `[]`). See `references[]` schema below. |

**Sorting**: After parsing, passages are sorted by `order` ascending. Duplicate orders are rejected.

### Passage content format

`content` is an **HTML string** (Tiptap-serialized, DOMPurify-safe). The rendering engine parses it with `DOMParser` and renders via `dangerouslySetInnerHTML`.

- **Reading passages**: standard `<p>` tags for paragraphs, plus heading-drop divs for `matching_heading` sections.
- **Listening transcripts**: plain text (no HTML tags required), typically prefixed with `[TRANSCRIPT]`.
- **`matching_heading` passages** require heading-drop blocks — see "Heading-Drop Contract" in `02-presentation-types.md`.

### `references[]`

Each reference links a passage snippet to a specific question:

```json
{
  "id": "11111111-1111-4111-8111-111111111111",
  "questionId": "22222222-2222-4222-8222-222222222222",
  "from": 0,
  "to": 120,
  "text": "The exact snippet of passage text relevant to this question"
}
```

| Field | Type | Rules |
|---|---|---|
| `id` | UUID v4 | Unique across all references in the passage. |
| `questionId` | UUID v4 | Must exist in the same part's `questions[].id`. |
| `from` | integer ≥ 0 | Best-effort character offset into `content`. |
| `to` | integer > `from` | Best-effort character offset into `content`. |
| `text` | string | **Load-bearing**. Must be a verbatim substring of `content`. The exam interface highlights passages by searching for this text. |

> **Critical**: `from`/`to` are best-effort. The rendering engine re-finds highlights by searching for `text` in the passage content. Always provide accurate `text`. If you cannot compute exact offsets, use 0/0 as defaults — `text` alone is sufficient.

---

## `sections[]`

```json
{
  "order": 1,
  "title": "Questions 1–5",
  "description": "Complete the notes below. Write NO MORE THAN TWO WORDS...",
  "presentationConfig": { "type": "...", ... }
}
```

| Field | Type | Rules |
|---|---|---|
| `order` | integer (1–100) | Sequential starting at 1, no gaps, no duplicates. |
| `title` | string | Required. Use "Questions X–Y" convention for question numbering. |
| `description` | string or `null` | Instructions from the exam paper. |
| `presentationConfig` | object | Required. Discriminated union on `"type"` — see `02-presentation-types.md`. |

**Constraints**:
- Every section must reference **at least one** question.
- A `questionId` may appear in **only one** section across the entire part.

---

## `questions[]`

```json
{
  "id": "11111111-1111-4111-8111-111111111111",
  "answerType": "text",
  "correctAnswer": ["answer"],
  "validation": {
    "maxWords": 2,
    "minWords": 1,
    "caseSensitive": false,
    "acceptedAnswers": ["alternative answer"]
  },
  "points": 1
}
```

| Field | Type | Rules |
|---|---|---|
| `id` | UUID v4 | **Required.** Must be unique across the **entire set** (not just this part). Client supplies; server never generates. |
| `answerType` | enum | Required. One of: `single_choice`, `multiple_choice`, `true_false_ng`, `yes_no_ng`, `text`. See mapping table below. |
| `correctAnswer` | string[] | Required. Min 1 element. For choices: **option letter(s)** (e.g. `["A"]` or `["A","C"]`). |
| `validation` | object | Optional. Only these keys allowed: `maxWords`, `minWords`, `caseSensitive`, `acceptedAnswers`. No other keys. |
| `points` | number or null | Optional. Numeric value. |

### `answerType` Mapping

| Presentation type | `answerType` |
|---|---|
| `single_choice` | `single_choice` |
| `multiple_choice` | `multiple_choice` |
| `select_from_list` | `multiple_choice` |
| `true_false_not_given` | `true_false_ng` |
| `yes_no_not_given` | `yes_no_ng` |
| Everything else | `text` |

### `correctAnswer` Conventions

| Question kind | `correctAnswer` value |
|---|---|
| Choice (`single_choice`) | `["A"]` (one letter) |
| Choice (`multiple_choice`) | `["A","C"]` (two+ letters) |
| TF/NG | `["TRUE"]`, `["FALSE"]`, or `["NOT GIVEN"]` |
| YN/NG | `["YES"]`, `["NO"]`, or `["NOT GIVEN"]` |
| Completion / short answer | `["expected word or phrase"]` |
| Matching heading | `["heading text from wordBank"]` |
| Matching features/info/sentence-end | `["feature letter from wordBank"]` |

---

## Cross-Entity Validation (superRefine)

These checks are enforced by `QEditorReplaceBodySchema` at parse time:

1. **Order contiguity**: Passage orders start at 1, are sequential, no gaps, no duplicates. Same for section orders.
2. **Section↔question references**: Every `questionId` in any section's `presentationConfig.items` must exist in `questions[].id`. The total count of referenced `questionIds` across ALL sections must **exactly equal** `questions.length`.
3. **No cross-section reuse**: No `questionId` may appear in more than one section.
4. **Every section has ≥ 1 question**.
5. **Blank/items match** (completion/grid types): Blank nodes in Tiptap `content` must match `items[]` in count and positional order. IDs must be identical.
6. **Uniqueness**: Every `questionId` is unique across the entire set (UUID v4).

---

## Hard Contracts (Summary)

These are non-negotiable rules derived from the schema and rendering code:

- **Tiptap native doc**: `presentationConfig.content` for completion/grid types must be `{"type":"doc","content":[...]}`, never HTML, never an object with an `html` field.
- **Blank nodes**: Exactly `{"type":"blank","attrs":{"questionId":"<uuid>"}}`. Inline atom nodes inside a paragraph/cell. Count MUST equal `items.length`. IDs must match positionally.
- **Choice answers are letters**: First option = A, second = B, etc. Never option text.
- **Matching wordBank conventions**: `matching_features`/`matching_information` → wordBank = label letters `["A","B","C","D","E"]`. `matching_heading` → wordBank = plain heading texts (no roman prefixes; renderer auto-numbers). Feature descriptions go in `description`, not in `wordBank.words`.
- **WordBank non-empty**: Never emit `{ "words": [], ... }` — omit the field entirely.
- **Validation keys**: Only `maxWords`, `minWords`, `caseSensitive`, `acceptedAnswers` — no extras.
- **No duplicate IDs**: Every `questionId` in `questions[]` must be globally unique across the set.
- **Heading-drop blocks**: For `matching_heading` sections, each item's `questionId` must appear exactly once as `<div data-type="heading-drop" data-question-id="<uuid>"></div>` in the part's passage HTML. See `02-presentation-types.md` for the full contract.
