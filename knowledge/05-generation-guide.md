# 05 — Question Set Generation Guide

This document governs how the AI **authors original IELTS question sets** (not converting PDFs). All content is original — never reproduce real past-exam material.

---

## Structure Table (Official IELTS Format)

| Skill | Type | Parts | Questions/part | Total |
|---|---|---|---|---|
| reading | academic | 3 passages | 13 / 13 / 14 | 40 |
| reading | general | 3 sections | 13–14 each | 40 |
| listening | all | 4 parts | 10 each | 40 |
| writing | all | 2 tasks | 1 each | 2 |
| speaking | all | 3 parts | 1 each | 3 |

---

## Typical Presentation Types by Skill

### Reading (academic/general)

- `true_false_not_given`, `yes_no_not_given`
- `single_choice`, `multiple_choice`
- `matching_heading`, `matching_information`, `matching_features`, `matching_sentence_end`
- `summary_completion`, `note_completion`, `sentence_completion`, `table_completion`
- `short_answers`, `select_from_list`

### Listening

- `form_completion`, `note_completion`, `table_completion`, `sentence_completion`
- `single_choice`, `multiple_choice`
- `matching_features`
- `map_plan_labeling`
- `short_answers`

### Writing

- `large_answers` (Task 1: chart description / letter; Task 2: essay prompt)

### Speaking

- `speaking_interview` (Part 1), `speaking_cue_card` (Part 2), `speaking_discussion` (Part 3)

---

## Content Quality Rules

### Passages (reading)

- **Academic**: 600–900 words. Use paragraph labels (A, B, C…) when the part uses `matching_heading` or `matching_information`.
- **General**: 500–800 words. More notice/form/table completion.
- Realistic academic/general register. Factual plausibility.

### Listening

Since no audio exists yet, write the full transcript into `passages[0].content`, prefixed with `[TRANSCRIPT]`. Sections should reference where answers occur via `references[]`.

### Section Descriptions

- `description` is **rich-text HTML** (Tiptap-serialized), never plain text — wrap instructions in `<p>` tags, use `<br>` for line breaks.
- Mirror real IELTS exam-paper instruction blocks: word-limit sentences ("Write NO MORE THAN TWO WORDS..."), letter ranges ("Choose the correct letter, A, B, C or D."), and TRUE/FALSE/NOT GIVEN meaning tables (as HTML `<table>`).
- For `multiple_choice`, state how many to choose in the description (e.g. `<p>Choose TWO letters, A-E.</p>`).
- Feature lists for `matching_features` and shared option pools go here as formatted HTML (`<strong>A.</strong> ...` per line), NOT in `wordBank.words`.
- Use `null` when a section genuinely has no instructions.

### Distractors (choice types)

- Plausible, no joke options, no "all of the above".
- Exactly one correct option for `single_choice`.
- 2+ correct options for `multiple_choice` — state how many in the section description (as HTML).

### Word Banks

Provide when the exam style calls for it; never empty. `reuse: false` means words are used exactly once — ensure bank size ≥ item count.

### Answer Keys

Every question gets a defensible `correctAnswer`. For open-ended text answers, add reasonable alternatives in `validation.acceptedAnswers`.

---

## Question Numbering

Implicit order = walk sections in order, collect item questionIds. Numbering must be **continuous across parts** of the same set (part 2 continues after part 1's last number). Reflect this in section titles like "Questions 14–26".

---

## Difficulty Escalation

Parts must escalate in difficulty:
- Part 1: easier
- Part 2: medium
- Part 3: harder

---

## UUID Generation

Every `questionId` must be a valid v4 UUID, unique across the **entire set** (not just the part). Pre-generate all UUIDs in your planning phase. Never reuse IDs across parts.

---

## Validation

Before delivering each part file, run `validate_part.py` on it. Only deliver at 0 errors.
