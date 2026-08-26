# 04 — PDF-to-JSON Conversion

This document governs the workflow for converting IELTS exam PDFs into the editor-replace JSON format. Follow these rules when the user uploads a PDF for extraction.

---

## Step 1: Analyze the PDF

Before generating JSON, internally determine:

1. **Passages** — reading source texts or listening transcripts. Number them in exam order.
2. **Sections** — question groups (e.g., "Questions 1–5"). Each section belongs to one passage and uses exactly ONE presentation type.
3. **Questions** — every individual answer slot. Each gets a unique UUID v4.
4. **Presentation type** per section — classify using the decision table below.
5. **Correct answers** — if the PDF contains an answer key; otherwise use expert judgment (see answer-key protocol below).

### Classification decision table

Misclassification is the most common conversion failure. Classify by the **PDF's visual cue**, not by surface wording:

| PDF cue | Presentation type | Notes |
|---|---|---|
| Question with its own 2+ options (radio/lettered list) | `single_choice` / `multiple_choice` | MCQ only when each question owns its options |
| Shared option box / dropdowns; several questions pick from ONE pool (often A–E in a box) | `select_from_list` | Options live at `presentationConfig.options`; each item is just `{questionId}`. NOT `multiple_choice`. |
| "Classify the following statements as referring to: A/B/C/D…" (esp. "You may use any letter more than once") | `matching_features` | Letter wordBank + `reuse: true`; feature list in description |
| "Which paragraph contains the following information?" | `matching_information` | Letter answers |
| List of headings (i–x) matched to paragraphs | `matching_heading` | Letter `questionText`, drop-zone divs, plain heading texts |
| Sentence beginnings + boxed endings (i–ix) | `matching_sentence_end` | |
| Blanks inside a table/grid/form layout | `table_completion` / `form_completion` | Native Tiptap table — do NOT flatten to sentences |
| Blanks inside flowing notes/summary/sentences | `note_completion` / `summary_completion` / `sentence_completion` | |
| Summary with a boxed A–P option list below | completion + **option-box convention** | wordBank = letters, mapping table in description (see `02` Family 3) |
| TRUE/FALSE/NOT GIVEN or YES/NO/NOT GIVEN statements | `true_false_not_given` / `yes_no_not_given` | |
| Labels on a diagram/map/flow-chart image | `diagram_completion` / `map_plan_labeling` / `flow_chart_completion` / `diagram_labeling` | |
| Short open questions ("What…?", "How many…?") | `short_answers` | |

When two types could apply, prefer the one that mirrors the PDF's **layout** (table vs list vs dropdown).

---

## Step 2: Content Fidelity & Source Grounding

**Preserve source content and terminology.** Do not silently replace the exam text with general knowledge. If the PDF is ambiguous or incomplete, make the most reasonable expert interpretation but keep the structure valid.

- Passages: preserve paragraph labels (A, B, C…) when present.
- Section instructions: copy verbatim from the PDF.
- Question text: copy verbatim.
- Distractors: keep the original options.

### Layout fidelity

Mirror the PDF's **visible structure** in the JSON:

- Question-range blocks are sacred: if the PDF shows "Questions 1–5" and "Questions 6–10" as separate boxed groups, they are **separate sections** — even if they share a format.
- Forms and tables in the PDF become Tiptap table structures (`table_completion` / `form_completion`) — never flatten them into plain sentence lines.
- Table titles/captions above a grid (e.g. "Companies", "Example: electric motorcycle") are preserved — inside the table or the section description, matching the page layout.
- Section descriptions preserve the PDF's rich formatting (bold, lists, tables) as Tiptap-compatible HTML.

### Source grounding (never fabricate)

- **Never fill missing passage/question pages from external websites.** If the uploaded PDF lacks the pages for a part, stop and ask the user to upload them.
- **Never emit placeholder content** — `"Option A"`, `"Option B"`, `"Question text here"` are forbidden. Every question's text and options must come from the PDF.
- If a separate answer-key file/image references a different test than the PDF, confirm the mismatch with the user before proceeding — do not silently combine two sources.
- Missing listening transcripts are the ONE exception: mark transcript content as unavailable (never invent audio script), and say so in the delivery message.

---

## Step 3: Answer Key Protocol

When the user uploads a PDF, check whether a reliable answer key is present.

### If answer key IS present

Map answers exactly. For choice questions, extract option letters. For completions, extract the exact word/phrase.

### If answer key is NOT present

Ask **exactly** this question (one time only):

> "Will you provide the answers/correct-answer key, or should AI populate the answers?"

**Two modes**:

| User choice | Behavior |
|---|---|
| **Key provided** | Map the user's answers exactly. |
| **AI populated** | Use expert IELTS knowledge to determine the best answers. Disclose in the chat message: "Answers are AI-generated and may need review." |

Never ask about the answer key more than once. If the user declines both, generate with AI-populated answers and disclose.

---

## Step 4: Classification Plan Gate (mandatory, every conversion)

Before generating ANY part file, present a **section→type mapping table** in chat and wait for the user's go-ahead:

```
Title: "MOCK 04 READING" — Reading, Academic

Part 1 (Passage 1: Extraction and Purification of Drinking Water)
  Q1–5    diagram_completion       (label the diagram, ≤3 words)
  Q6–11   matching_features        (classify A–D, reuse: true)
  Q12–13  select_from_list         (choose TWO from A–E)

Part 2 …
```

Rules:
- One row per question-range block, exactly as the PDF groups them.
- State the presentation type and the decisive cue (shared box, grid layout, "more than once", etc.).
- For option-box completions, state that letters + mapping-table description will be used.
- **Stop and wait** for confirmation ("go" / corrections). If the user corrects a type, re-emit the table before generating.
- Do not regenerate parts one-by-one hoping classification is right — the gate exists to catch misclassification before files exist.

## Step 5: Present as Part Files

Follow the delivery protocol in `03-delivery-protocol.md`:

1. Break the exam into parts (each passage = one part for reading; each section = one part for listening).
2. Generate one JSON file per part.
3. Run `validate_part.py` on each file.
4. Deliver validated files only.

---

## Step 6: Handling Images / Diagrams

When the PDF contains images, diagrams, or maps:

1. **Extract the original image when possible** — crop the diagram/chart from the PDF page as a standalone high-resolution PNG (upscale if low quality). Deliver it as a file alongside the JSON so the user can upload it to the asset server after import.
2. Use a descriptive placeholder for `assetId`: `"TODO-upload-diagram-p1-q3"` and reference the extracted PNG in the chat message.
3. Use the appropriate visual presentation type (`map_plan_labeling`, `diagram_completion`, etc.).
4. Set `markerLayout` based on the image layout (see `02-presentation-types.md`).
5. Note in the chat message which images need to be manually uploaded after import.

---

## Listening PDFs

When the PDF is an IELTS listening paper:

1. **Transcript**: Extract the audio script. Place it in `passages[0].content` as a plain text block prefixed with `[TRANSCRIPT]`.
2. **Questions**: Extract as usual, following part-by-part structure (Part 1–4).
3. **Transcript delivery**: Also deliver the transcript as a separate `.txt` file in `@prepx-audio v1` format (see `06-listening-transcript.md`).

---

## Writing / Speaking PDFs

- **Writing**: two tasks → **two separate part files** (one per task), following the production convention (see `examples/writing-day-one-part-*.json`):
  - `passages[0]` carries the prompt: `title` = the task topic/question, `content` = the remaining task instructions as HTML (including the chart image `<img>` for Task 1 if available).
  - `sections[0]`: `title` = `"Written Response"`, `presentationConfig.type` = `large_answers`, `items[0].questionText` = exactly `"Write your response below."`
  - `questions[0]`: `answerType` = `text`, `correctAnswer` = `["Sample response placeholder"]`, `validation` = `{ "minWords": 150, "caseSensitive": false }` for Task 1 / `minWords: 250` for Task 2.
  - The prompt is NOT a reading passage and NOT the `questionText` — do not model it any other way.
- **Speaking**: Three parts. Each part = one section with the appropriate speaking type.
