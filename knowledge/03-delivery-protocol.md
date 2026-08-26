# 03 — Delivery Protocol

This document governs **how outputs are delivered** — the protocol for file generation, part-by-part orchestration, validation, and chat interaction. Every workflow (PDF conversion, AI generation) must follow this protocol.

---

## Rule #1: Files, Not Chat JSON

Every generated part must be delivered as a **downloadable file**, never as raw JSON printed in chat.

- Use code interpreter to write the JSON to a file.
- Run `validate_part.py` on every file **before** linking it.
- Chat message: concise status + file link only.
- **Never** print the full JSON artifact into chat unless the user explicitly asks to see raw JSON.

---

## Rule #2: One Part Per File

Each JSON file contains **one part only**, with exactly three keys: `passages`, `sections`, `questions`. Do NOT wrap the artifact in a `{ "part": ..., "progress": ..., "nextAction": ... }` envelope — those protocol fields were a v1 mistake and are rejected by the editor.

### File naming convention

```
<set-code>-part-<partNumber>.json
```

Examples:
- `ielts-r-academic-001-part-1.json`
- `ielts-r-academic-001-part-2.json`
- `ielts-l-academic-002-part-1.json`

For listening transcript files (`.txt`):
```
<set-code>-part-<partNumber>-transcript.txt
```

### Versioned filenames on regeneration (mandatory)

The platform **caches artifacts by filename** — if you regenerate a file but keep the same name, the delivered link re-serves the OLD cached version and the user will report "file is not updated". Therefore:

- The **first** delivery of a part uses the base name (`…-part-2.json`).
- Every **subsequent regeneration** of that part MUST use a new versioned filename: `…-part-2-v2.json`, `…-part-2-v3.json`, …
- Never overwrite a file and re-link it under the same name.
- Tell the user explicitly which version to use ("use the v3 file, not v2").

### Verify-after-write (mandatory)

After writing any regenerated file and before linking it:

1. **Re-read the file from disk** (fresh open, not the in-memory object) and confirm the intended change is actually present in the serialized JSON.
2. Run `validate_part.py` on it.
3. Only then deliver the link.

Claiming a fix without verifying the serialized file on disk is a delivery failure — in-memory edits do not always reach the file.

---

## Part-by-Part Generation Protocol

When generating a full question set, follow this multi-turn protocol:

### Phase 1: Metadata (ask once)

If not provided by the user, ask once before generating anything:

- **skill**: `reading` | `listening` | `writing` | `speaking`
- **type**: `academic` | `general`
- **title**: display title

Do not ask for these again in subsequent turns.

### Phase 2: The Plan

Emit a compact plan as a chat message (not a JSON file):

```
IELTS Reading — Academic
Title: "Climate Change Impacts"

Part 1 (Passage 1): 13 questions — TF/NG, Summary Completion
Part 2 (Passage 2): 13 questions — MCQ, Matching Information
Part 3 (Passage 3): 14 questions — Matching Heading, Sentence Completion

Total: 40 questions | 3 parts

Ready to generate Part 1.
```

Then **stop**. Wait for user confirmation (e.g. "generate part 1").

### Phase 3: Generate Parts

For each requested part:
1. Generate the part JSON.
2. Write it to a file via code interpreter.
3. Re-read the file from disk and verify the content (verify-after-write).
4. Run `validate_part.py <filename>`.
5. If 0 errors → deliver file link + concise message. Report any validator **warnings** in the same message.
6. If errors → fix, use a NEW versioned filename, re-validate. Never deliver a file that failed validation.

### Phase 4: Complete

After the final part, state completion with a summary:

```
All 3 parts generated and validated.
- ielts-r-academic-001-part-1.json — 13 questions ✓
- ielts-r-academic-001-part-2.json — 13 questions ✓
- ielts-r-academic-001-part-3.json — 14 questions ✓

Import each into the Question Editor via JSON Editor dialog.
```

---

## Validation Gate

Before delivering any file, run the validator:

```python
# In code interpreter
import validate_part
result = validate_part.validate_file("filename.json")
print(result)
```

**Only deliver if `errors` is empty.** Warnings are non-blocking but MUST be reported to the user in the delivery message (they usually indicate a likely misclassification, e.g. choice questions that should be `select_from_list`). If validation fails:
- Report the specific error(s) to the user.
- Fix the JSON.
- Re-validate with a NEW versioned filename.
- Deliver only after clean validation.

See `validate_part.py` for the full rule set.

---

## PDF Conversion Delivery

When converting a PDF:
1. Analyze the PDF content first.
2. Ask about missing answer keys (one question, one time).
3. Generate parts following the same file-per-part protocol.
4. Each part file is a valid `{ passages, sections, questions }` object.
5. Transcript content (listening) goes into `passages[0].content`, prefixed with `[TRANSCRIPT]`.

---

## Listening Transcripts

When generating listening parts:
1. Deliver the transcript as a separate `.txt` file in `@prepx-audio v1` format.
2. Deliver the question set part as a separate `.json` file.
3. Both files must be validated independently.

The transcript format is defined in `06-listening-transcript.md`.

---

## Chat Style

- Concise, technical, neutral.
- Status messages: brief confirmation of what was generated.
- Error reports: observed behavior → applicable rule → exact fix.
- Do not explain the schema in chat unless asked. Reference the docs.
