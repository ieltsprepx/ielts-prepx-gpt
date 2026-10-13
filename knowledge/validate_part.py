"""
validate_part.py — Validates a question-set part JSON against QEditorReplaceBodySchema rules.

Usage (in GPT code interpreter):
    import validate_part
    result = validate_part.validate_file("part.json")
    print(result)

Or standalone:
    python validate_part.py part.json [--transcript transcript.txt]

Exit code: 0 = valid, 1 = errors found.
Stdlib only — no external dependencies.
"""

import json
import re
import sys
import uuid
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_ANSWER_TYPES = {"single_choice", "multiple_choice", "true_false_ng", "yes_no_ng", "text"}
VALID_VALIDATION_KEYS = {"maxWords", "minWords", "caseSensitive", "acceptedAnswers"}
VALID_PRESENTATION_TYPES = {
    "short_answers", "large_answers",
    "multiple_choice", "single_choice", "select_from_list",
    "true_false_not_given", "yes_no_not_given",
    "note_completion", "summary_completion", "sentence_completion",
    "table_completion", "form_completion",
    "matching_features", "matching_heading",
    "matching_sentence_end", "matching_information",
    "matching_features_tabular", "matching_information_tabular",
    "diagram_completion", "flow_chart_completion",
    "map_plan_labeling", "diagram_labeling",
    "speaking_interview", "speaking_cue_card", "speaking_discussion",
}

# Types where presentationConfig has items[].questionText
TYPES_WITH_QUESTION_TEXT = {
    "short_answers", "large_answers",
    "multiple_choice", "single_choice",
    "true_false_not_given", "yes_no_not_given",
    "matching_features", "matching_heading",
    "matching_sentence_end", "matching_information",
    "matching_features_tabular", "matching_information_tabular",
    "diagram_completion", "flow_chart_completion",
    "map_plan_labeling", "diagram_labeling",
    "speaking_interview", "speaking_cue_card", "speaking_discussion",
}

# Types where presentationConfig has Tiptap content + items[].questionId only
TYPES_WITH_BLANKS = {
    "note_completion", "summary_completion", "sentence_completion",
    "table_completion", "form_completion",
}

# Types requiring wordBank (required object, not optional)
TYPES_REQUIRING_WORD_BANK = {
    "matching_features", "matching_heading",
    "matching_sentence_end", "matching_information",
    "matching_features_tabular", "matching_information_tabular",
}

# Types where options are shared pool
TYPES_WITH_SHARED_OPTIONS = {"select_from_list"}

# Types with options per item
TYPES_WITH_ITEM_OPTIONS = {"single_choice", "multiple_choice"}

# Visual types
TYPES_VISUAL = {
    "diagram_completion", "flow_chart_completion",
    "map_plan_labeling", "diagram_labeling",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_valid_uuid_v4(s: str) -> bool:
    try:
        parsed = uuid.UUID(s)
        return parsed.version == 4
    except (ValueError, AttributeError):
        return False


def walk_tiptap_blanks(content: Any) -> list[str]:
    """Recursively walk a Tiptap document, collecting blank questionIds in document order."""
    blanks: list[str] = []
    if isinstance(content, dict):
        if content.get("type") == "blank":
            qid = (content.get("attrs") or {}).get("questionId")
            if qid:
                blanks.append(qid)
        for child in content.get("content", []):
            blanks.extend(walk_tiptap_blanks(child))
    elif isinstance(content, list):
        for item in content:
            blanks.extend(walk_tiptap_blanks(item))
    return blanks


def find_number_markers_before_blanks(content: Any) -> list[str]:
    """Text nodes directly preceding a blank that still carry a "(N)" marker.

    The blank node renders the question number itself — the marker is
    redundant and renders as "(31) [blank]".
    """
    found: list[str] = []
    tail_res = [re.compile(r"\s*\(\d{1,2}\)\s*[:.]?\s*$"), re.compile(r"\s\d{1,2}[.)]\s*$")]

    def scan(arr: list) -> None:
        for i in range(len(arr) - 1):
            cur, nxt = arr[i], arr[i + 1]
            if (
                isinstance(cur, dict)
                and cur.get("type") == "text"
                and isinstance(nxt, dict)
                and nxt.get("type") == "blank"
            ):
                text = str(cur.get("text", ""))
                if any(r.search(text) for r in tail_res):
                    found.append(text[-30:])
        for el in arr:
            if isinstance(el, dict) and isinstance(el.get("content"), list):
                scan(el["content"])

    if isinstance(content, dict) and isinstance(content.get("content"), list):
        scan(content["content"])
    return found


def find_empty_text_nodes(content: Any, path: str = "$") -> list[str]:
    """Find empty text nodes ({"type":"text","text":""}) anywhere in a Tiptap document.

    These make the editor reject/drop the entire document (renders empty).
    """
    found: list[str] = []
    if isinstance(content, dict):
        if content.get("type") == "text" and content.get("text", "") == "":
            found.append(path)
        for key, value in content.items():
            if key == "content" and isinstance(value, list):
                for i, child in enumerate(value):
                    found.extend(find_empty_text_nodes(child, f"{path}.content[{i}]"))
            elif isinstance(value, (dict, list)):
                found.extend(find_empty_text_nodes(value, f"{path}.{key}"))
    elif isinstance(content, list):
        for i, item in enumerate(content):
            found.extend(find_empty_text_nodes(item, f"{path}[{i}]"))
    return found


LETTER_RE = re.compile(r"^[A-Z]$")


def letter_index(letter: str) -> int:
    """Option letter (A=0, B=1, ...) → index into an options array."""
    return ord(letter) - ord("A")


def has_gaps(orders: list[int]) -> bool:
    if not orders:
        return False
    sorted_o = sorted(orders)
    return sorted_o[0] != 1 or any(sorted_o[i + 1] - sorted_o[i] != 1 for i in range(len(sorted_o) - 1))


def has_duplicates(orders: list[int]) -> bool:
    return len(orders) != len(set(orders))


def find_heading_drop_ids(html: str) -> list[str]:
    """Extract data-question-id values from heading-drop divs in passage HTML.

    Attribute order is not guaranteed — the platform serializes
    data-question-id before data-type. Match any <div ...> containing both.
    """
    if not html or not isinstance(html, str):
        return []
    ids: list[str] = []
    for tag in re.findall(r"<div\b[^>]*>", html):
        attrs = dict(re.findall(r'([a-zA-Z-]+)="([^"]*)"', tag))
        if attrs.get("data-type") == "heading-drop" and attrs.get("data-question-id"):
            ids.append(attrs["data-question-id"])
    return ids


# ---------------------------------------------------------------------------
# Main validation
# ---------------------------------------------------------------------------

def validate(data: dict) -> dict:
    errors: list[str] = []
    warnings: list[str] = []

    # --- Top-level keys ---
    top_keys = set(data.keys())
    if top_keys != {"passages", "sections", "questions"}:
        errors.append(f"Top-level keys must be {{passages, sections, questions}}, got {top_keys}")

    passages = data.get("passages", [])
    sections = data.get("sections", [])
    questions = data.get("questions", [])

    # --- Passages ---
    p_orders = []
    for i, p in enumerate(passages):
        if "order" not in p:
            errors.append(f"passages[{i}].order is missing")
        else:
            p_orders.append(p["order"])
        if "title" not in p or not isinstance(p.get("title"), str) or not p["title"]:
            errors.append(f"passages[{i}].title must be a non-empty string")
        if "content" not in p or not isinstance(p.get("content"), str):
            errors.append(f"passages[{i}].content must be a string")
        else:
            m = re.match(r"^\s*<p[^>]*>([\s\S]*?)</p>", p.get("content") or "", re.I)
            if m and p.get("title"):
                first_plain = re.sub(r"<[^>]+>", " ", m.group(1))
                first_plain = re.sub(r"\s+", " ", first_plain).strip().lower()
                title_plain = re.sub(r"\s+", " ", str(p["title"])).strip().lower()
                if first_plain and title_plain and first_plain == title_plain:
                    warnings.append(
                        f"passages[{i}]: the first content paragraph repeats the passage title "
                        f"{p['title']!r} — the title renders separately; drop the duplicated paragraph"
                    )
        # references
        refs = p.get("references", [])
        if not isinstance(refs, list):
            errors.append(f"passages[{i}].references must be an array")
        for j, ref in enumerate(refs):
            if "id" not in ref:
                errors.append(f"passages[{i}].references[{j}].id is missing")
            if "questionId" not in ref:
                errors.append(f"passages[{i}].references[{j}].questionId is missing")
            if "text" not in ref or not isinstance(ref.get("text"), str) or not ref["text"]:
                errors.append(f"passages[{i}].references[{j}].text must be a non-empty string")

    if p_orders:
        if has_gaps(p_orders):
            errors.append(f"Passage orders must be contiguous starting at 1, got: {sorted(p_orders)}")
        if has_duplicates(p_orders):
            errors.append(f"Duplicate passage orders: {p_orders}")

    # --- Sections ---
    s_orders = []
    for i, s in enumerate(sections):
        if "order" not in s:
            errors.append(f"sections[{i}].order is missing")
        else:
            s_orders.append(s["order"])
        if "title" not in s or not isinstance(s.get("title"), str):
            errors.append(f"sections[{i}].title is missing (empty string is fine)")
        elif re.match(r"^questions?\s+\d{1,2}\b", s.get("title", "").strip(), re.I):
            warnings.append(
                f"sections[{i}].title {s['title']!r} duplicates the auto-generated question-range header — "
                f"leave the title empty"
            )
        if "description" not in s:
            errors.append(f"sections[{i}].description is missing (can be null)")

    if s_orders:
        if has_gaps(s_orders):
            errors.append(f"Section orders must be contiguous starting at 1, got: {sorted(s_orders)}")
        if has_duplicates(s_orders):
            errors.append(f"Duplicate section orders: {s_orders}")

    # --- Questions ---
    question_ids: set[str] = set()
    q_id_list: list[str] = []
    q_by_id: dict[str, dict] = {}
    for i, q in enumerate(questions):
        qid = q.get("id", "")
        if not qid:
            errors.append(f"questions[{i}].id is missing")
            continue
        if not is_valid_uuid_v4(qid):
            errors.append(f"questions[{i}].id is not a valid UUID v4: {qid}")
        if qid in question_ids:
            errors.append(f"questions[{i}].id is a duplicate: {qid}")
        question_ids.add(qid)
        q_id_list.append(qid)
        q_by_id[qid] = q

        at = q.get("answerType", "")
        if at not in VALID_ANSWER_TYPES:
            errors.append(f"questions[{i}].answerType invalid: {at}")

        ca = q.get("correctAnswer")
        if not isinstance(ca, list) or len(ca) < 1:
            errors.append(f"questions[{i}].correctAnswer must be a non-empty array")

        if "validation" not in q:
            errors.append(f"questions[{i}].validation is required (use {{}} if empty)")
            continue

        val = q.get("validation")
        if not isinstance(val, dict):
            errors.append(f"questions[{i}].validation must be an object")
        else:
            extra = set(val.keys()) - VALID_VALIDATION_KEYS
            if extra:
                errors.append(f"questions[{i}].validation has invalid keys: {extra}")

    # --- Cross-entity: section questionId references ---
    ref_count = 0
    seen_in_section: set[str] = set()
    for i, s in enumerate(sections):
        config = s.get("presentationConfig", {})
        ptype = config.get("type", "")
        items = config.get("items", [])
        if not items:
            errors.append(f"sections[{i}].presentationConfig.items is empty")
            continue

        for j, item in enumerate(items):
            rqid = item.get("questionId", "")
            if not rqid:
                errors.append(f"sections[{i}].presentationConfig.items[{j}].questionId is missing")
                continue
            if rqid not in question_ids:
                errors.append(f"sections[{i}].presentationConfig.items[{j}].questionId {rqid} not found in questions[]")
            if rqid in seen_in_section:
                errors.append(f"questionId {rqid} appears in multiple sections")
            seen_in_section.add(rqid)
            ref_count += 1

    if questions and ref_count != len(questions):
        errors.append(f"Total questionId references in sections ({ref_count}) != questions.length ({len(questions)})")

    # --- Presentation config validation per type ---
    for i, s in enumerate(sections):
        config = s.get("presentationConfig", {})
        ptype = config.get("type", "")
        items = config.get("items", [])
        if ptype not in VALID_PRESENTATION_TYPES:
            errors.append(f"sections[{i}].presentationConfig.type invalid: {ptype}")
            continue

        # --- Warning: "more than once" instruction vs reuse flag ---
        desc = s.get("description") or ""
        wb_any = config.get("wordBank")
        if (
            isinstance(desc, str)
            and "more than once" in desc.lower()
            and isinstance(wb_any, dict)
            and wb_any.get("reuse") is not True
        ):
            warnings.append(
                f"sections[{i}]: description says 'more than once' but wordBank.reuse is not true (got {wb_any.get('reuse')})"
            )

        # --- Warning: statement type vs the description's meaning table ---
        if ptype in ("true_false_not_given", "yes_no_not_given"):
            plain_desc = re.sub(r"<[^>]+>", " ", str(desc or "")).lower()
            has_yes = re.search(r"(^|\W)yes(\W|$)", plain_desc)
            has_no = re.search(r"(^|\W)no(\W|$)", plain_desc)
            if ptype == "true_false_not_given" and has_yes and has_no:
                warnings.append(
                    f"sections[{i}]: type is 'true_false_not_given' but the description labels the options "
                    f"YES / NO / NOT GIVEN — this is a 'yes_no_not_given' task; flip the type and remap answers (TRUE→YES, FALSE→NO)"
                )
            if ptype == "yes_no_not_given" and not (has_yes and has_no):
                warnings.append(
                    f"sections[{i}]: type is 'yes_no_not_given' but the description has no YES/NO labels — "
                    f"verify the meaning table (TRUE/FALSE tasks must be 'true_false_not_given')"
                )

        # Blank types (completion/grid)
        if ptype in TYPES_WITH_BLANKS:
            content = config.get("content")
            if not isinstance(content, dict) or content.get("type") != "doc":
                errors.append(f"sections[{i}]: completion type requires content.type === 'doc', got {type(content)}")
            else:
                empty_nodes = find_empty_text_nodes(content)
                for ep in empty_nodes:
                    errors.append(
                        f"sections[{i}]: empty text node at {ep} — {{\"text\":\"\"}} makes the editor drop the whole document; use a paragraph with no content array instead"
                    )
                blanks = walk_tiptap_blanks(content)
                if len(blanks) != len(items):
                    errors.append(f"sections[{i}]: blank count ({len(blanks)}) != items.length ({len(items)})")
                else:
                    for k, item in enumerate(items):
                        item_qid = item.get("questionId", "")
                        if k < len(blanks) and blanks[k] != item_qid:
                            errors.append(f"sections[{i}]: blank[{k}] questionId {blanks[k]} != items[{k}].questionId {item_qid}")
                for tail in find_number_markers_before_blanks(content):
                    warnings.append(
                        f"sections[{i}]: text node ends with a question-number marker {tail!r} right before a blank — "
                        f"the blank renders the number itself; strip the '(N)' marker from the text"
                    )
                if isinstance(desc, str) and re.search(r"list of (words|phrases|options)", desc, re.I) and not config.get("wordBank"):
                    warnings.append(
                        f"sections[{i}]: instruction says a word list is given but wordBank is missing — "
                        f"add the option-box wordBank (letters) or drop the word list from the instruction"
                    )
                for para in content.get("content", []) or []:
                    if not isinstance(para, dict) or para.get("type") != "paragraph":
                        continue
                    first = next(
                        (c for c in para.get("content", []) or []
                         if isinstance(c, dict) and c.get("type") == "text"),
                        None,
                    )
                    if first and re.match(r"^\s*(?:[•·]|o)(\s+|$)", str(first.get("text", ""))):
                        warnings.append(
                            f"sections[{i}]: paragraph starts with a literal bullet {first.get('text','')[:10]!r} — "
                            f"use bulletList/listItem nodes instead of '• '/'o ' text (nest 'o' items inside the parent listItem)"
                        )

        # items[] must contain ONLY questionId (importer rejects extra keys)
        if ptype in TYPES_WITH_BLANKS or ptype in TYPES_WITH_SHARED_OPTIONS:
            for j, item in enumerate(items):
                extra_keys = set(item.keys()) - {"questionId"}
                if extra_keys:
                    errors.append(
                        f"sections[{i}].presentationConfig.items[{j}] has extra keys {sorted(extra_keys)} — only 'questionId' is allowed for {ptype}"
                    )

        # Choice with item options
        if ptype in TYPES_WITH_ITEM_OPTIONS:
            for j, item in enumerate(items):
                opts = item.get("options", [])
                if len(opts) < 2:
                    errors.append(f"sections[{i}].items[{j}].options must have ≥2 elements")
                for k, opt in enumerate(opts):
                    if not isinstance(opt, str) or not opt.strip():
                        errors.append(f"sections[{i}].items[{j}].options[{k}] must be a non-empty string")
                # Letter answers must exist within the item's options pool
                q = q_by_id.get(item.get("questionId", ""))
                if q is not None:
                    for ans in q.get("correctAnswer", []):
                        if LETTER_RE.fullmatch(str(ans)) and letter_index(ans) >= len(opts):
                            errors.append(
                                f"sections[{i}].items[{j}]: correctAnswer '{ans}' is outside the options pool ({len(opts)} options)"
                            )
            # Warning: multiple_choice items sharing identical options → likely select_from_list
            if ptype == "multiple_choice":
                opt_lists = [json.dumps(item.get("options", []), sort_keys=True) for item in items]
                if len(opt_lists) != len(set(opt_lists)):
                    warnings.append(
                        f"sections[{i}]: multiple_choice items share identical options arrays — if these are answer slots picking from one shared pool, use 'select_from_list' instead"
                    )
                # Duplicate stems → answer slots, not distinct questions
                stems = [(item.get("questionText") or "").strip() for item in items]
                dup_stems = {t for t in stems if t and stems.count(t) > 1}
                if dup_stems:
                    errors.append(
                        f"sections[{i}]: multiple_choice items have duplicate questionText {sorted(dup_stems)[:1]!r} — repeated stems are answer "
                        f"slots sharing one pool; use 'select_from_list' (stem in description, bare questionId items)"
                    )

        # Shared options
        if ptype in TYPES_WITH_SHARED_OPTIONS:
            opts = config.get("options", [])
            if len(opts) < 2:
                errors.append(f"sections[{i}].presentationConfig.options must have ≥2 elements")
            for k, opt in enumerate(opts):
                if not isinstance(opt, str) or not opt.strip():
                    errors.append(f"sections[{i}].presentationConfig.options[{k}] must be a non-empty string (not an object)")
            # A shared pool attached to flowing text with blanks is a completion
            # (option-box convention) — never select_from_list.
            plain_desc = re.sub(r"<[^>]+>", " ", str(desc or ""))
            has_blank_markers = bool(
                re.search(r"[.…]{4,}|\.{4,}|_{3,}|\(?\b\d{1,2}[\).]\s*[.…]{2,}", plain_desc)
            )
            if has_blank_markers:
                errors.append(
                    f"sections[{i}]: type is 'select_from_list' but the description contains flowing text with "
                    f"blank markers — this is a summary/note completion with a word box; use "
                    f"summary_completion/note_completion (Tiptap doc + wordBank of LETTERS per the option-box "
                    f"convention), not select_from_list"
                )
            for item in items:
                q = q_by_id.get(item.get("questionId", ""))
                if q is not None:
                    ca = q.get("correctAnswer", [])
                    if len(ca) > 1:
                        errors.append(
                            f"sections[{i}]: select_from_list slot has {len(ca)} correct answers {ca!r} — each slot takes "
                            f"exactly ONE option (distribute combined keys like '21 & 22 → B, D' one letter per slot)"
                        )
                    for ans in ca:
                        if LETTER_RE.fullmatch(str(ans)) and letter_index(ans) >= len(opts):
                            errors.append(
                                f"sections[{i}]: correctAnswer '{ans}' is outside the shared options pool ({len(opts)} options)"
                            )

        # Statement types: canonical literals
        if ptype in ("true_false_not_given",):
            allowed = {"TRUE", "FALSE", "NOT GIVEN"}
            for item in items:
                q = q_by_id.get(item.get("questionId", ""))
                if q is not None:
                    for ans in q.get("correctAnswer", []):
                        if str(ans).upper() not in allowed:
                            errors.append(f"sections[{i}]: true_false_not_given answer must be one of TRUE/FALSE/NOT GIVEN, got: {ans!r}")
                        elif ans not in allowed:
                            warnings.append(f"sections[{i}]: statement answer {ans!r} should use canonical uppercase form")
        if ptype in ("yes_no_not_given",):
            allowed = {"YES", "NO", "NOT GIVEN"}
            for item in items:
                q = q_by_id.get(item.get("questionId", ""))
                if q is not None:
                    for ans in q.get("correctAnswer", []):
                        if str(ans).upper() not in allowed:
                            errors.append(f"sections[{i}]: yes_no_not_given answer must be one of YES/NO/NOT GIVEN, got: {ans!r}")
                        elif ans not in allowed:
                            warnings.append(f"sections[{i}]: statement answer {ans!r} should use canonical uppercase form")

        # Matching types
        if ptype in TYPES_REQUIRING_WORD_BANK:
            wb = config.get("wordBank")
            if not isinstance(wb, dict):
                errors.append(f"sections[{i}]: matching type requires wordBank")
            else:
                words = wb.get("words", [])
                if not isinstance(words, list) or len(words) == 0:
                    errors.append(f"sections[{i}].wordBank.words must be a non-empty array")
                else:
                    for k, w in enumerate(words):
                        if not isinstance(w, str) or not w.strip():
                            errors.append(f"sections[{i}].wordBank.words[{k}] must be a non-empty string")
                if isinstance(words, list) and words:
                    for item in items:
                        q = q_by_id.get(item.get("questionId", ""))
                        if q is not None:
                            for ans in q.get("correctAnswer", []):
                                if ans not in words:
                                    errors.append(
                                        f"sections[{i}]: correctAnswer {ans!r} not found in wordBank.words — answers must exactly match a wordBank entry"
                                    )

        # matching_sentence_end: items carry the sentence beginnings / item labels
        if ptype == "matching_sentence_end":
            for j, item in enumerate(items):
                qt = str(item.get("questionText", "") or "").strip()
                if not qt:
                    errors.append(
                        f"sections[{i}].items[{j}].questionText is required for matching_sentence_end "
                        f"(the sentence beginning / item text — never a bare questionId)"
                    )

        # matching_heading: heading-drop blocks in passage content
        if ptype == "matching_heading":
            for j, item in enumerate(items):
                qt = item.get("questionText", "")
                if not re.fullmatch(r"[A-Z]", str(qt).strip()):
                    errors.append(
                        f"sections[{i}].items[{j}].questionText must be a single paragraph letter (A, B, C, ...), got: {qt!r}"
                    )
            item_ids = {item.get("questionId", "") for item in items if item.get("questionId")}
            drop_ids = []
            for passage in passages:
                pcontent = passage.get("content", "")
                drop_ids.extend(find_heading_drop_ids(pcontent))
            drop_set = set(drop_ids)
            for qid in item_ids:
                if qid not in drop_set:
                    errors.append(f"sections[{i}]: matching_heading item {qid} has no heading-drop block in passage content")
            for qid in drop_ids:
                if not qid:
                    errors.append(f"sections[{i}]: empty data-question-id in heading-drop block")
                elif drop_ids.count(qid) > 1:
                    errors.append(f"sections[{i}]: heading-drop block {qid} appears {drop_ids.count(qid)} times (expected 1)")

        # Visual types
        if ptype in TYPES_VISUAL:
            asset_id = config.get("assetId", "")
            if not asset_id:
                errors.append(f"sections[{i}]: visual type requires assetId")
            ml = config.get("markerLayout")
            if ml == "question_list":
                for j, item in enumerate(items):
                    if not item.get("questionText"):
                        errors.append(f"sections[{i}].items[{j}].questionText required when markerLayout=question_list")
                    if "position" in item:
                        errors.append(f"sections[{i}].items[{j}].position forbidden when markerLayout=question_list")
            elif ml in ("on_image", "below_image", None):
                for j, item in enumerate(items):
                    if "position" not in item:
                        errors.append(f"sections[{i}].items[{j}].position required when markerLayout={ml}")

        # Writing: large_answers carry NO correct answer — the model answer
        # lives in the explanation's grading guide (PROMPT: / MODEL ANSWER:)
        if ptype == "large_answers":
            for q in questions:
                expl = str(q.get("explanation", "") or "").strip()
                ca = [str(a) for a in q.get("correctAnswer", [])]
                joined = " ".join(ca).strip()
                if joined:
                    errors.append(
                        "questions: large_answers correctAnswer must be [\"\"] (empty) — "
                        "writing questions have no correct answer; the model answer belongs "
                        "in the explanation's MODEL ANSWER section"
                    )
                if not expl:
                    errors.append(
                        f"questions: large_answers question is missing 'explanation' — the AI writing "
                        f"grader uses it as the grading guide; add PROMPT + band-7 model answer"
                    )
                elif "sample response placeholder" in expl.lower():
                    errors.append("questions: large_answers explanation is still the placeholder — write the band-7 model answer")
                else:
                    if not re.search(r"prompt\s*:", expl, re.I):
                        errors.append("questions: large_answers explanation lacks 'PROMPT:' — the grader needs the full task prompt")
                    if not re.search(r"model answer\s*:?", expl, re.I):
                        errors.append("questions: large_answers explanation lacks 'MODEL ANSWER:' — the grader needs a band-7 model answer")
            body_html = " ".join(str(p.get("content", "")) for p in passages)
            prompt_text = " ".join(str(p.get("title", "")) for p in passages)
            if "<img" not in body_html and re.search(
                r"graph|chart|table|diagram|process|map|compare|summarise|summarize",
                prompt_text + " " + body_html,
                re.I,
            ):
                warnings.append(
                    "passages: this looks like a Task 1 visual prompt but the content has no <img> — "
                    "students cannot answer without seeing the graph/chart"
                )

        # Speaking cue_card
        if ptype == "speaking_cue_card":
            if not config.get("topic"):
                errors.append(f"sections[{i}]: speaking_cue_card requires topic")
            bp = config.get("bulletPoints", [])
            if not isinstance(bp, list) or len(bp) == 0:
                errors.append(f"sections[{i}]: speaking_cue_card requires bulletPoints")

    return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


def validate_file(path: str) -> str:
    """Validate a JSON file and return a formatted result string."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return f"INVALID: JSON syntax error at line {e.lineno}, col {e.colno}: {e.msg}"
    except FileNotFoundError:
        return f"INVALID: file not found: {path}"

    result = validate(data)
    out_lines: list[str] = []
    if result["valid"]:
        out_lines.append(f"VALID: {path}")
    else:
        out_lines.append(f"INVALID: {path} — {len(result['errors'])} error(s):")
        for err in result["errors"]:
            out_lines.append(f"  - {err}")
    if result.get("warnings"):
        out_lines.append(f"WARNING: {len(result['warnings'])} warning(s) (non-blocking, report to user):")
        for warn in result["warnings"]:
            out_lines.append(f"  - {warn}")
    return "\n".join(out_lines)


# ---------------------------------------------------------------------------
# Transcript validation (@prepx-audio v1)
# ---------------------------------------------------------------------------

def validate_transcript(path: str) -> str:
    """Validate a @prepx-audio v1 transcript file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        return f"INVALID: file not found: {path}"

    errors: list[str] = []
    lines = content.split("\n")

    if not lines or lines[0].strip() != "@prepx-audio v1":
        errors.append("First line must be '@prepx-audio v1'")

    declared_speakers: set[str] = set()
    speakers: dict[str, str] = {}
    in_script = False
    current_speaker: str | None = None
    pause_re = re.compile(r"\[pause\s+[\d.]+(?:s|ms)\]")

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("@speaker "):
            sid = stripped.split("@speaker ", 1)[1].strip()
            declared_speakers.add(sid)
        elif stripped == "@script":
            in_script = True
        elif in_script and stripped.startswith("[") and stripped.endswith("]"):
            inner = stripped[1:-1]
            # Skip standalone pause directives like [pause 0.5s]
            if pause_re.match(stripped):
                pass
            else:
                current_speaker = inner
                if inner not in declared_speakers:
                    errors.append(f"Line {i}: speaker '{inner}' not declared with @speaker")
        elif stripped and not stripped.startswith("@") and not stripped.startswith("["):
            if current_speaker is None:
                errors.append(f"Line {i}: speech text before any speaker selected")
            # Check pause syntax inline
            for match in pause_re.finditer(stripped):
                pass  # valid pause
            if "[pause" in stripped and not pause_re.search(stripped):
                # Check for malformed pause
                bad_pauses = re.findall(r"\[pause[^\]]*\]", stripped)
                for bp in bad_pauses:
                    errors.append(f"Line {i}: malformed pause directive: {bp}")

    if not declared_speakers:
        errors.append("No @speaker declarations found")

    if errors:
        lines_out = [f"INVALID: {path} — {len(errors)} error(s):"]
        for err in errors:
            lines_out.append(f"  - {err}")
        return "\n".join(lines_out)
    return f"VALID: {path}"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Validate IELTS question-set part JSON or transcript")
    parser.add_argument("file", help="JSON file (part) or .txt file (transcript)")
    parser.add_argument("--transcript", action="store_true", help="Validate as @prepx-audio v1 transcript")
    args = parser.parse_args()

    if args.transcript:
        out = validate_transcript(args.file)
        print(out)
        sys.exit(0 if out.startswith("VALID") else 1)
    elif args.file.endswith(".json"):
        out = validate_file(args.file)
        print(out)
        sys.exit(0 if out.startswith("VALID") else 1)
    else:
        out = validate_transcript(args.file)
        print(out)
        sys.exit(0 if out.startswith("VALID") else 1)
