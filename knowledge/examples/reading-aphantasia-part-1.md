# Markdown-form counterpart of `reading-aphantasia-part-1.json`

This is the **Markdown + markers** authoring input (per `08-authoring-markdown.md`) that produces
content equivalent to `reading-aphantasia-part-1.json` — kept here as the reference "what you
actually write" counterpart to that JSON "what gets stored" example. Aliases below (`q1`..`q13`)
are the ones the plan/server would hand you; you never invent your own numbering.

---

## Passage (`p1`)

```markdown
Close your eyes and imagine walking along a sandy beach and then gazing over the horizon as the
Sun rises. How clear is the image that springs to mind?

Most people can readily conjure images inside their head — known as their mind's eye. But this
year scientists have described a condition, aphantasia, in which some people are unable to
visualise mental images.

Niel Kenmuir, from Lancaster, has always had a blind mind's eye. He knew he was different even in
childhood. "My stepfather, when I couldn't sleep, told me to count sheep, and he explained what he
meant, I tried to do it and I couldn't," he says.
```

Notice: plain paragraphs only, no markers — a Reading passage never contains `[[qN]]` (those only
belong in a completion/grid section's `body`), and no `[[heading:qN]]` either unless this part also
has a `matching_heading` section (it doesn't, here).

---

## Section `s1` — `true_false_not_given` (Questions 1-8)

Stem-type section: no `body`, no markers — one plain-text `stem` per item.

```
item q1  stem: "Aphantasia is a condition, which describes people, for whom it is hard to visualise mental images."          answer: ["TRUE"]
item q2  stem: "Niel Kenmuir was unable to count sheep in his head."                                                          answer: ["TRUE"]
item q3  stem: "People with aphantasia struggle to remember personal traits and clothes of different people."                 answer: ["FALSE"]
```

(Full 8-item section abbreviated for this example — the JSON counterpart shows all 8.)

`section.instructions` (Markdown → HTML):

```markdown
Do the following statements agree with the information given in the passage?
```

---

## Section `s2` — `sentence_completion` (Questions 9-13)

Body-type section: the `body` field is Markdown prose with inline `[[qN]]` markers, one blank per
sentence, in the same left-to-right order as `items[]`.

```markdown
Only a small fraction of people have imagination as [[q9]] as Lauren does.

Hyperphantasia is [[q10]] to aphantasia.

There are a lot of subjectivity in comparing people's imagination — somebody's vivid scene could be
another's [[q11]].
```

`section.instructions`:

```markdown
Complete the sentences below.

Write **NO MORE THAN TWO WORDS** from the passage for each answer.
```

Items (answer text, not letters — this is a completion type):

```
item q9   answer: ["vivid"]
item q10  answer: ["opposite"]     acceptedAnswers: ["the opposite"]
item q11  answer: ["dull scene"]
```

---

## What the converter produces

Running this through `markdownToHtml()`/`markdownToTiptapDoc()` (the backend's one-way converter,
§4 of `docs/ai-question-generation-plan.md`) yields exactly the JSON shapes in
`reading-aphantasia-part-1.json`'s `passages[0].content` (HTML `<p>` tags) and
`sections[1].presentationConfig.content` (a native Tiptap `doc` with inline `blank` atoms
positionally matching `items[]`) — the Markdown above is what an AI-generation session (or a human
using file mode) actually writes; the JSON file is what ends up stored.
