# 02 — Presentation Config Catalog (All 24 Types)

`presentationConfig` is a discriminated union on the `"type"` field. This document defines the exact JSON shape for every type. Follow each shape precisely — the schema validates strictly.

> Derived from: `presentation-config/index.ts`, `common.ts`, `answers-schema.ts`, `choice-schema.ts`, `statement-schema.ts`, `completion-schema.ts`, `grid-schema.ts`, `matching-schema.ts`, `visual-schema.ts`, `speaking-schema.ts`

---

## Family 1: Statement Types

### `true_false_not_given` / `yes_no_not_given`

```json
{
  "type": "true_false_not_given",
  "items": [
    { "questionId": "<uuid>", "questionText": "The statement text..." }
  ]
}
```

- `items`: min 1 element. Each has `questionId` (UUID) and `questionText` (non-empty string).
- `correctAnswer`: `["TRUE"]`, `["FALSE"]`, or `["NOT GIVEN"]` (or `["YES"]`/`["NO"]` for yes/no).
- `answerType`: `true_false_ng` or `yes_no_ng` respectively.

---

## Family 2: Choice Types

### `single_choice`

```json
{
  "type": "single_choice",
  "items": [
    {
      "questionId": "<uuid>",
      "questionText": "Question text...",
      "options": ["Option A text", "Option B text", "Option C text"]
    }
  ]
}
```

- `items`: min 1. `options`: min 2 non-empty strings. Do NOT include letter prefixes ("A", "B") in the option text.
- `correctAnswer`: **letter(s)** — first option = A, second = B, etc. For single choice: exactly one letter. E.g. `["B"]`.
- `answerType`: `single_choice`.

### `multiple_choice`

Same shape as `single_choice`. The section description must state how many to choose (e.g. "Choose TWO letters").

- `correctAnswer`: two+ letters. E.g. `["A","C"]`.
- `answerType`: `multiple_choice`.

### `select_from_list`

Shared option pool; each item is just an answer slot:

```json
{
  "type": "select_from_list",
  "options": ["Shared option 1", "Shared option 2", "Shared option 3"],
  "items": [{ "questionId": "<uuid>" }]
}
```

- `options`: min 2 non-empty strings.
- `items`: min 1. Each has only `questionId`.
- `correctAnswer`: **letter(s)** derived from `options` array. E.g. `["C"]`.
- `answerType`: **`multiple_choice`** (assigned by the editor's select-from-list builder; each slot picks a letter from the pool).

---

## Family 3: Completion Types

### `note_completion` / `summary_completion` / `sentence_completion`

Blanks live inside a Tiptap JSON document. `items` mirrors every blank in document order.

```json
{
  "type": "note_completion",
  "content": {
    "type": "doc",
    "content": [
      {
        "type": "paragraph",
        "content": [
          { "type": "text", "marks": [], "text": "Text before blank " },
          { "type": "blank", "attrs": { "questionId": "<uuid>" } },
          { "type": "text", "marks": [], "text": " text after blank." }
        ]
      }
    ]
  },
  "items": [
    { "questionId": "<uuid>" },
    { "questionId": "<uuid>" }
  ],
  "wordBank": { "words": ["word1", "word2"], "reuse": false }
}
```

**Hard rules**:
- `content` MUST be a native Tiptap `{"type":"doc",...}` document — **never HTML**, never an object with an `html` field.
- Blank nodes: exactly `{"type":"blank","attrs":{"questionId":"<uuid>"}}`. Inline atom nodes.
- **Blank count MUST equal `items.length`**. IDs must match positionally in document order. No duplicate blank IDs.
- `items` contains `{ "questionId": "<uuid>" }` only (no `questionText` — text lives in the template).
- `sentence_completion`: each paragraph = one sentence containing exactly one blank.
- `wordBank` is **optional** — omit entirely if no word bank. Never emit `{ "words": [], ... }`.

---

## Family 4: Grid Types

### `table_completion` / `form_completion`

Same rules as completion types, but `content` is a Tiptap table structure:

```json
{
  "type": "table_completion",
  "content": {
    "type": "doc",
    "content": [
      {
        "type": "table",
        "content": [
          {
            "type": "tableRow",
            "content": [
              {
                "type": "tableHeader",
                "content": [
                  {
                    "type": "paragraph",
                    "content": [
                      { "type": "text", "text": "Header text" }
                    ]
                  }
                ]
              },
              {
                "type": "tableCell",
                "content": [
                  {
                    "type": "paragraph",
                    "content": [
                      { "type": "text", "text": "Cell text " },
                      { "type": "blank", "attrs": { "questionId": "<uuid>" } }
                    ]
                  }
                ]
              }
            ]
          }
        ]
      }
    ]
  },
  "items": [{ "questionId": "<uuid>" }]
}
```

- Header rows use `"tableHeader"` instead of `"tableCell"`.
- Blanks mirror `items` in document (reading) order.
- Same blank count / positional match rules as completion types.

---

## Family 5: Matching Types

All matching configs require a **required** `wordBank` (not optional). Every type uses `answerType: "text"`.

### `matching_heading` (special — passage interaction)

Students match paragraph droppable slots to headings. This type is unique: it embeds answer-slot blocks **inside the passage content**, not in the section config alone.

```json
{
  "type": "matching_heading",
  "wordBank": { "words": ["The origins of tea", "Global tea trade", "Health effects"], "reuse": false },
  "items": [
    { "questionId": "<uuid-1>", "questionText": "This paragraph discusses how tea was first cultivated in ancient China." },
    { "questionId": "<uuid-2>", "questionText": "The passage describes the expansion of tea across continents." }
  ]
}
```

**Hard rules — `matching_heading` only**:
1. **`items`** = paragraph droppable slots. Each item's `questionId` must have **exactly one** `<div data-type="heading-drop" data-question-id="<uuid>">` block placed in the part's passage HTML content, **immediately before (on top of) the paragraph it belongs to** — never after the paragraph. The builder warns when a heading has no drop zone or shares one with another heading.
2. **`wordBank.words`** = heading texts **without roman numeral prefixes**. The renderer auto-numbers them (i, ii, iii…). E.g. `["The origins of tea", "Global trade"]` — NOT `["i. The origins of tea"]`.
3. **`correctAnswer`** = exact heading text from `wordBank.words`. E.g. `["The origins of tea"]`.
4. **Passage content must be HTML** with the heading-drop divs placed **immediately before** their paragraphs (drop zone renders on top). Example passage content:

```html
<div data-type="heading-drop" data-question-id="<uuid-1>"></div>
<p>Tea is one of the most widely consumed beverages in the world.</p>
<div data-type="heading-drop" data-question-id="<uuid-2>"></div>
<p>The practice of drinking tea has a long history in China.</p>
<div data-type="heading-drop" data-question-id="<uuid-3>"></div>
<p>By the seventeenth century, tea had become popular across Europe.</p>
```

5. **`reuse`**: typically `false` (headings used once; bank larger than paragraph count).

### Other matching types

```json
{
  "type": "matching_features",
  "wordBank": { "words": ["A", "B", "C", "D", "E"], "reuse": false },
  "items": [
    { "questionId": "<uuid>", "questionText": "Statement text to match..." }
  ]
}
```

### Types and semantics

| Type | `items[].questionText` | `wordBank.words` | `correctAnswer` | `reuse` |
|---|---|---|---|---|
| `matching_heading` | Paragraph description | **Heading texts** (no roman prefix) | Heading text | `false` |
| `matching_information` | Statement text | Paragraph letters ("A","B",...) | Letter | usually `true` |
| `matching_features` | Statement/item text | **Label letters only** ("A","B",...) | Letter | `false` |
| `matching_sentence_end` | Sentence beginnings | Sentence endings | Ending text | `false` |
| `matching_features_tabular` | Same as `matching_features` | Same | Same | Same |
| `matching_heading_tabular` | Same as `matching_heading` | Same | Same | Same |
| `matching_information_tabular` | Same as `matching_information` | Same | Same | Same |

**Hard rules**:
- `matching_features`: the shared feature list is described in the section `description`, NOT in `wordBank.words`. WordBank contains only label letters `["A","B","C","D","E"]`. Correct answer is the letter.
- `matching_information`: same letter pattern as features — `wordBank.words` = paragraph letters, `correctAnswer` = letter.
- Tabular variants are identical in schema, rendered as two-column tables. Prefer tabular when PDF shows table layout.
- `wordBank` is **required** for all matching types (not optional field — required object).
- `items`: min 1 element, each with `questionId` and `questionText`.

---

## Family 6: Visual / Image Types

### `diagram_completion` / `flow_chart_completion` / `map_plan_labeling` / `diagram_labeling`

```json
{
  "type": "map_plan_labeling",
  "title": "Floor plan of the library",
  "assetId": "TODO-upload-map-image",
  "markerLayout": "on_image",
  "items": [
    {
      "questionId": "<uuid>",
      "questionText": "Label text (if markerLayout allows)",
      "position": { "x": 42, "y": 30 },
      "width": 8,
      "height": 6
    }
  ],
  "wordBank": { "words": ["Reception", "Studio"], "reuse": false }
}
```

**Rules**:
- `assetId`: required non-empty string. Use descriptive placeholder like `"TODO-upload-map-p1"` when no image available.
- `markerLayout`:
  - `"on_image"` / `"below_image"` (default): each item REQUIRES `position {x, y}` (0–100 percentage coordinates). `questionText` optional.
  - `"question_list"`: each item REQUIRES `questionText`; `position` **forbidden**. Use for pre-labeled images (letters baked into the asset).
- `width`/`height`: optional 0–100 pin sizes.
- `wordBank`: optional (omit if no word bank).

---

## Family 7: Answer Types

### `short_answers` / `large_answers`

```json
{
  "type": "short_answers",
  "items": [
    { "questionId": "<uuid>", "questionText": "What is the maximum height of...?" }
  ]
}
```

- `items`: min 1. Each has `questionId` and `questionText` (non-empty).
- `answerType`: `text`.

---

## Family 8: Speaking Types

### `speaking_interview` / `speaking_discussion`

```json
{
  "type": "speaking_interview",
  "items": [
    { "questionId": "<uuid>", "questionText": "Do you work or are you a student?" }
  ]
}
```

### `speaking_cue_card`

```json
{
  "type": "speaking_cue_card",
  "topic": "Describe a book you recently read.",
  "bulletPoints": [
    "what the book is about",
    "why you read it",
    "whether you would recommend it"
  ],
  "prepTimeSeconds": 60,
  "speakingTimeSeconds": 120,
  "items": [
    { "questionId": "<uuid>", "questionText": "Follow-up question..." }
  ]
}
```

- `topic`: min 1 non-empty string.
- `bulletPoints`: min 1 non-empty strings.
- `prepTimeSeconds` / `speakingTimeSeconds`: integers ≥ 0.

---

## Blank Node Specification (All Completion/Grid Types)

Every blank node in Tiptap `content` must be exactly:

```json
{ "type": "blank", "attrs": { "questionId": "<uuid>" } }
```

**Properties**:
- `type`: literal `"blank"`.
- `attrs.questionId`: UUID matching the corresponding `items[]` entry.
- Inline atom node (group: "inline", inline: true, atom: true in Tiptap schema).
- Rendered as `<span data-type="blank" data-question-id="<uuid>">` in the editor.

### Validation algorithm

To verify blank↔items match:
1. Walk `content` recursively, collecting all nodes with `type === "blank"` in document order.
2. Assert `blankCount === items.length`.
3. Assert `blanks[i].attrs.questionId === items[i].questionId` for every index.
4. Assert no duplicate blank IDs.

---

## Quick Reference: Type → answerType

| Type | `answerType` |
|---|---|
| `single_choice` | `single_choice` |
| `multiple_choice` | `multiple_choice` |
| `select_from_list` | `multiple_choice` |
| `true_false_not_given` | `true_false_ng` |
| `yes_no_not_given` | `yes_no_ng` |
| Everything else | `text` |
