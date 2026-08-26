# IELTS PrepX GPT

Knowledge base and configuration for the IELTS PrepX custom GPT.

## Structure

```
gpt/
├── gpt-config/
│   ├── instructions.md      # Pasted into GPT "Instructions" (≤8000 chars)
│   └── settings.md          # Name, description, starters, capabilities
├── knowledge/               # Uploaded to GPT Knowledge + hosted on GitHub
│   ├── 00-index.md          # Doc map, task routing
│   ├── 01-schema-entities.md
│   ├── 02-presentation-types.md
│   ├── 03-delivery-protocol.md
│   ├── 04-pdf-to-json.md
│   ├── 05-generation-guide.md
│   ├── 06-listening-transcript.md
│   ├── 07-strict-rules.md
│   ├── validate_part.py
│   └── examples/
└── .backup/                 # v1 archive (git-ignored)
```

## Setup

1. Push this repo to GitHub (public) as the live KB source.
2. In `gpt-config/instructions.md`, replace `<OWNER>/<REPO>` with your GitHub repo path — this is the **only** edit needed.
3. Paste `gpt-config/instructions.md` into the GPT's Instructions field.
4. Upload all `knowledge/` files to the GPT's Knowledge.
5. Enable: Code Interpreter, Web Browsing.

## Update workflow

1. Edit docs in `knowledge/`.
2. Commit with a conventional commit (e.g. `fix(kb): correct matching_heading wordBank`).
3. Push to GitHub. Live immediately.
4. Re-upload snapshot to GPT only on major changes.

## Note on `instructions.md`

`instructions.md` is intentionally static — it contains only behavioral rules that
are product-level invariants (files-not-chat, validate-before-deliver, fetch-first).
All schema, protocol, and format rules live in `knowledge/` and are fetched at
conversation start via the fetch-first rule. **Do not add schema details to
instructions.md** — they belong in the KB and will go stale there instead.
