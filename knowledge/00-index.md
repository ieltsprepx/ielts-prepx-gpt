# IELTS PrepX Knowledge Base — Index

---

## Document Map

| Doc | Purpose | When to read |
|---|---|---|
| `01-schema-entities.md` | Canonical entity schemas (passages/sections/questions), cross-entity rules, answerType mapping | **Always** — every task |
| `02-presentation-types.md` | All 24 presentation types with exact JSON shapes and hard contracts | **Always** — every generation or conversion |
| `03-delivery-protocol.md` | File delivery protocol, part-by-part rules, validation gate, naming conventions | **Always** — every output |
| `04-pdf-to-json.md` | PDF conversion workflow, answer-key protocol, image handling | PDF upload tasks |
| `05-generation-guide.md` | Authoring original question sets, structure table, quality rules | AI generation tasks |
| `06-listening-transcript.md` | `@prepx-audio v1` transcript format for TTS audio | Listening skill tasks |
| `07-strict-rules.md` | Consolidated rules, edge cases, common pitfalls | **Always** — every generation or conversion |
| `examples/` | 9 production-validated part files (reading/writing/listening) + pattern notes | **Always** — ground truth for shape and conventions |
| `validate_part.py` | Python validator — run on every generated file before delivery | Every file delivery |

---

## Task Routing

| User asks to... | Read these docs |
|---|---|
| Convert a PDF to JSON | 01, 02, 03, 04, 07 |
| Generate an original question set | 01, 02, 03, 05, 07 |
| Generate a listening part | 01, 02, 03, 05, 06, 07 |
| Review/validate an existing JSON | 01, 02, 07, examples/, validate_part.py |
| Generate a listening transcript | 06, 07 |
| Study a worked example | examples/ |

---

## Critical Rules (Summary)

1. **Files, not chat JSON.** Every artifact is delivered as a file via code interpreter.
2. **Validate before deliver.** Run `validate_part.py` on every file. 0 errors = deliver. Report warnings in the delivery message.
3. **One part per file.** `{ passages, sections, questions }` only. No wrappers.
4. **Letters for choices.** `correctAnswer` = option letters (A, B, C…), not text.
5. **Tiptap native doc.** Completion/grid content = `{"type":"doc",...}`, never HTML.
6. **Blank positional match.** Blank nodes in content must match `items[]` by count, order, and ID.
7. **Heading-drop blocks.** For `matching_heading`, passage HTML must include exactly one `<div data-type="heading-drop" data-question-id="<uuid>"></div>` per item, placed **immediately before (on top of) its paragraph**. Words in wordBank are plain heading texts (no roman prefix).
8. **Passage content is HTML.** Reading passage content uses `<p>` tags. References search the plain-text extraction of the HTML.

---

## MCP Clients

The same knowledge base is served to MCP clients (ChatGPT connectors, Claude, IDE agents) by the PrepX backend's MCP server via read-only tools: `authoring_guide` (these docs), `authoring_examples` / `authoring_example` (the validated artifacts). MCP clients must follow the fetch-first rule equivalently: read `index`, then `schema_entities`, `presentation_types`, and `strict_rules` before generating. Content is fetched live from this repository with a bundled snapshot fallback — keeping this repo authoritative for both the custom GPT and MCP surfaces.
9. **No empty text nodes.** `{"text":""}` anywhere in Tiptap content makes the editor render the section empty. Empty line/cell = paragraph with no `content` array.
10. **Versioned filenames on regeneration.** The platform caches artifacts by filename — every regenerated file gets a NEW name (`-v2`, `-v3`…), then verify-after-write (re-read from disk) before delivering.
11. **Classification plan gate.** Every PDF conversion presents a section→type mapping table and waits for user confirmation BEFORE generating (see `04-pdf-to-json.md` Step 4).
12. **Source grounding.** Never fill missing PDF content from the web or placeholders; never invent transcripts. Ask for the complete source.
