# 04 — PDF-to-JSON Conversion

This document governs the workflow for converting IELTS exam PDFs into the editor-replace JSON format. Follow these rules when the user uploads a PDF for extraction.

---

## Step 1: Analyze the PDF

Before generating JSON, internally determine:

1. **Passages** — reading source texts or listening transcripts. Number them in exam order.
2. **Sections** — question groups (e.g., "Questions 1–5"). Each section belongs to one passage and uses exactly ONE presentation type.
3. **Questions** — every individual answer slot. Each gets a unique UUID v4.
4. **Presentation type** per section — classify using the catalog in `02-presentation-types.md`.
5. **Correct answers** — if the PDF contains an answer key; otherwise use expert judgment (see answer-key protocol below).

---

## Step 2: Content Fidelity

**Preserve source content and terminology.** Do not silently replace the exam text with general knowledge. If the PDF is ambiguous or incomplete, make the most reasonable expert interpretation but keep the structure valid.

- Passages: preserve paragraph labels (A, B, C…) when present.
- Section instructions: copy verbatim from the PDF.
- Question text: copy verbatim.
- Distractors: keep the original options.

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

## Step 4: Present as Part Files

Follow the delivery protocol in `03-delivery-protocol.md`:

1. Break the exam into parts (each passage = one part for reading; each section = one part for listening).
2. Generate one JSON file per part.
3. Run `validate_part.py` on each file.
4. Deliver validated files only.

---

## Step 5: Handling Images / Diagrams

When the PDF contains images, diagrams, or maps:

1. Create a descriptive placeholder for `assetId`: `"TODO-upload-diagram-p1-q3"`.
2. Use the appropriate visual presentation type (`map_plan_labeling`, `diagram_completion`, etc.).
3. Set `markerLayout` based on the image layout (see `02-presentation-types.md`).
4. Note in the chat message which images need to be manually uploaded after import.

---

## Listening PDFs

When the PDF is an IELTS listening paper:

1. **Transcript**: Extract the audio script. Place it in `passages[0].content` as a plain text block prefixed with `[TRANSCRIPT]`.
2. **Questions**: Extract as usual, following part-by-part structure (Part 1–4).
3. **Transcript delivery**: Also deliver the transcript as a separate `.txt` file in `@prepx-audio v1` format (see `06-listening-transcript.md`).

---

## Writing / Speaking PDFs

- **Writing**: Two tasks. Each task = one `large_answers` section with one question. Include the task prompt in `questionText`.
- **Speaking**: Three parts. Each part = one section with the appropriate speaking type.
