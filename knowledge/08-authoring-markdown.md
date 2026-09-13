# 08 — Authoring in Markdown + Markers (Primary Authoring Format)

This is the **primary authoring instruction** for producing question-set content — both for this
custom GPT (server mode, see `03-delivery-protocol.md`) and for the PrepX backend's AI Question
Generation feature, which converts exactly this grammar into real editor JSON via a shared,
one-way converter. `02-presentation-types.md` remains the reference for the underlying JSON shapes,
but you should no longer author raw Tiptap JSON by hand — write Markdown, and the converter (or, in
file mode, your own understanding of `02`) produces the JSON.

> **One-way only.** Markdown → editor JSON conversion exists. Editor JSON → Markdown does **not**,
> and never will for existing hand-authored content — see the rationale in the backend's
> `docs/ai-question-generation-plan.md` §1.3 if curious. Practically: you only ever need to _write_
> Markdown, never read it back out of something a human already edited.

---

## 1. Supported Markdown subset

Only these constructs are recognized. Anything else (raw HTML, footnotes, strikethrough, task
lists, blockquotes, images) is either stripped or passed through as literal text — don't rely on it.

| Markdown                          | Renders as                                                                                                                     |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| Paragraphs (blank line separated) | `<p>`                                                                                                                          |
| `**bold**`                        | `<strong>`                                                                                                                     |
| `_italic_` / `*italic*`           | `<em>`                                                                                                                         |
| `` `code` ``                      | `<code>`                                                                                                                       |
| `##` / `###` / `####`             | `<h2>` / `<h3>` / `<h4>` (levels beyond `h4` collapse to `h4`, `h1` promotes to `h2` — the editor schema only registers h2–h4) |
| `- item` / `1. item`              | `<ul>`/`<ol>` + `<li>`                                                                                                         |
| GFM tables (`\| a \| b \|`)       | `<table>` with a `<thead>` from the header row                                                                                 |
| Soft/hard line breaks             | `<br>`                                                                                                                         |

No raw HTML. No underline (the editor has an underline mark, but nothing in this grammar can
produce it — that is a deliberate, known gap, not an oversight).

---

## 2. The two conversion targets

Where your Markdown ends up depends on which field you're writing:

| Field                                                              | Shape                              | Notes                                                                            |
| ------------------------------------------------------------------ | ---------------------------------- | -------------------------------------------------------------------------------- |
| Passage `content`                                                  | HTML (the subset above)            | May contain `[[heading:qN]]` markers (§4)                                        |
| Section `description`                                              | HTML (the subset above)            | Free-form instructions/context                                                   |
| Completion/grid `content` (note/summary/sentence/table_completion) | Native Tiptap `{"type":"doc",...}` | Built from Markdown containing `[[qN]]` markers (§3) — **never write HTML here** |

Everything else (question stems, options, word banks, answers) is plain text — no Markdown needed.

---

## 3. The `[[qN]]` blank marker

Used **only** inside a completion/grid type's body markdown (`note_completion`,
`summary_completion`, `sentence_completion`, `table_completion`). Write it exactly where the blank
belongs, using the question's alias:

```
The museum was founded in [[q7]] by a local [[q8]].
```

For `table_completion`, write a normal GFM table with markers inside cells:

```
| Name | Age |
| --- | --- |
| Alice | [[q9]] |
```

Rules:

- Every alias you were given for this section **must appear exactly once**, in the same order as
  the `items[]` array you also produce — position in the text is what determines which question a
  blank belongs to; get this order right, there is no separate ID field to fall back on.
- Never leave a paragraph or table cell with only a blank and no surrounding words unless the
  section genuinely calls for it (e.g. `sentence_completion`'s "one blank per sentence").
- Do not invent extra blanks or omit any you were given.

---

## 4. The `[[heading:qN]]` marker (matching_heading only)

`matching_heading`/`matching_heading_tabular` embed their answer slots **inside the passage**, not
in the section body. Write the marker on its own line, immediately before the paragraph it belongs
to:

```
[[heading:q11]]

(A) Tea is one of the most widely consumed beverages in the world.

[[heading:q12]]

(B) The practice of drinking tea has a long history in China.
```

The marker becomes an invisible heading-drop zone rendered on top of the paragraph that follows it
— never write it after the paragraph, and never share one marker between two paragraphs. Passage
paragraphs referenced this way should already carry a visible label matching the item's `stem`
("A", "B", …) inside the paragraph text itself, e.g. `(A) …`.

---

## 5. Per-family authoring notes

- **Statement** (`true_false_not_given`/`yes_no_not_given`): plain text stem per item, no markers.
  Answer is exactly one of `TRUE`/`FALSE`/`NOT GIVEN` or `YES`/`NO`/`NOT GIVEN`.
- **Choice** (`single_choice`/`multiple_choice`): plain text stem + options (no letter prefixes in
  the option text itself). Answer is the letter(s) of the correct option(s), first option = A.
- **`select_from_list`**: items carry **no stem** — the shared option pool lives once at the
  section level. Answer is the letter of the correct pool entry for each item.
- **Completion** (`note_completion`/`summary_completion`/`sentence_completion`/`table_completion`):
  see §3. Answer is the actual accepted text, not a letter.
- **`short_answers`**: plain text stem, answer is the actual accepted text.
- **`large_answers`** (Writing task): a single item whose stem is the task prompt; there is no
  single machine-checkable answer, use a placeholder like `N/A`.
- **Matching** (`matching_features`/`matching_information`/`matching_sentence_end` and their
  `_tabular` variants): stem is the statement/label text; a `wordBank` (the pool the student
  matches against) is **required**, never optional. Answer is the matching wordBank entry (or its
  letter, if the bank is itself letters).
- **`matching_heading`**: see §4. Stem is the **paragraph letter**, never a description. WordBank
  is heading texts with **no roman-numeral prefix** — the renderer numbers them itself.
- **Visual** (`diagram_completion`/`flow_chart_completion`/`map_plan_labeling`/`diagram_labeling`):
  **never reference a real image.** Instead describe an `assetGap` — `kind`, `purpose`, a
  ready-to-paste `generationPrompt`, and `altText`. A human fills in the real asset later; nothing
  here ever invents pixels. Choose `markerLayout: on_image`/`below_image` (each item needs
  `position {x,y}`, 0–100 percentage coordinates) or `question_list` (each item needs a stem
  instead, no position).
- **Speaking** (`speaking_interview`/`speaking_cue_card`/`speaking_discussion`): stem is the
  question/follow-up prompt text, no markers. `answer` is an unused placeholder (`N/A`) since
  spoken responses aren't machine-graded against one string. `speaking_cue_card` additionally
  needs section-level `topic`, `bulletPoints` (2-4 short prompts), `prepTimeSeconds` (usually `60`)
  and `speakingTimeSeconds` (usually `120`); its items are the examiner's follow-up questions.

---

## 6. Validation you get for free vs. validation you must get right yourself

The server (or, in file mode, `validate_part.py`) checks: blank count matches `items.length`,
positional order, no duplicate blank IDs, no empty text nodes, required fields per type (e.g.
`wordBank` for matching, `assetId` for visual once filled). You are still responsible for getting
the **grammar** right — the marker text, the table shape, the paragraph boundaries — since that's
what the converter reads to build the JSON in the first place.
