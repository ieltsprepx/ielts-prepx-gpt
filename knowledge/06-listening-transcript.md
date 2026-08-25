# 06 — Listening Transcript Format (`@prepx-audio v1`)

This document defines the text-file format for listening transcripts, used by the TTS audio generation system. When generating listening parts, deliver the transcript as a separate `.txt` file conforming to this format.

---

## Format Specification

### Required Structure

```
@prepx-audio v1

@speaker <id>
@voice <gender>, <language>, <traits>

@script

[speaker_id]
<speech text>

<pause_directive>
```

### Header

First line must be exactly: `@prepx-audio v1`

### Speaker Declaration

Each speaker must be declared before `@script`:

```
@speaker <id>
@voice <gender>, <language>, <traits>
```

| Component | Values |
|---|---|
| `id` | Lowercase single-word: `examiner`, `candidate`, `receptionist`. Max 32 chars. |
| `gender` | `male` or `female` |
| `language` | `british`, `american`, or other English variety |
| `traits` | Voice characteristics matching the Kokoro catalog |

**Trait options by context**:
- Professional: `professional`, `confident`, `well-rounded`
- Friendly: `warm`, `friendly`, `expressive`
- Calm: `calm`, `professional`
- Conversational: `conversational`, `natural`, `casual`

### Script Section

After `@script`, each speech segment starts with `[speaker_id]` followed by the speech text. Pauses use `[pause <duration>]` with `s` or `ms` units.

---

## Pause Rules

### When to use pauses

| Situation | Duration |
|---|---|
| Speaker transitions | 0.4–0.6s (default) |
| Topic shifts | 0.5–0.8s |
| Emphasis | 0.3–0.4s |
| Dramatic effect | 1.0–2.0s |

### Inline vs standalone

**Inline** (within a speaker's turn):
```
[receptionist]
Good morning. [pause 0.3s] How can I help you today?
```

**Standalone** (between speakers or major transitions):
```
[receptionist]
The main entrance is on the north side.

[pause 0.5s]

[caller]
Thank you. I also need information about the parking.
```

---

## Speech Writing Rules

- Use contractions: "I'm", "You're", "Can't", "Won't"
- Keep sentences 10–20 words optimal
- Use punctuation for prosody: commas (short pauses), periods (falling intonation), question marks (rising), ellipses (hesitation)
- Avoid overly formal language unless character-appropriate
- Include natural pauses between speakers and topic shifts

---

## IELTS Listening Template

```
@prepx-audio v1

@speaker examiner
@voice female, british, professional

@speaker candidate
@voice male, british, conversational

@script

[examiner]
Welcome to the IELTS listening test. You will hear a conversation about accommodation options.
[pause 0.8s]
Listen carefully and answer the questions as you listen.

[pause 1.0s]

[candidate]
Hello. I'm calling about student housing for the upcoming semester.
```

---

## Delivery

When generating a listening part:
1. Deliver the transcript as `<set-code>-part-N-transcript.txt`.
2. Deliver the question set as `<set-code>-part-N.json`.
3. Both must be validated independently.

The JSON part's `passages[0].content` should contain the transcript text (plain, without the `@prepx-audio` header directives), prefixed with `[TRANSCRIPT]`.

---

## Validation

Run transcript validation:
```python
import validate_part
result = validate_part.validate_transcript("transcript.txt")
print(result)
```

Checks:
- First line is `@prepx-audio v1`
- All speakers declared before use
- Valid pause format (`[pause 0.5s]` or `[pause 500ms]`)
- No speech before first speaker selection
- No duplicate speaker IDs
