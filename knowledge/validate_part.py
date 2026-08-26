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
        if "title" not in s or not isinstance(s.get("title"), str) or not s["title"]:
            errors.append(f"sections[{i}].title must be a non-empty string")
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

        # Blank types
        if ptype in TYPES_WITH_BLANKS:
            content = config.get("content")
            if not isinstance(content, dict) or content.get("type") != "doc":
                errors.append(f"sections[{i}]: completion type requires content.type === 'doc', got {type(content)}")
            else:
                blanks = walk_tiptap_blanks(content)
                if len(blanks) != len(items):
                    errors.append(f"sections[{i}]: blank count ({len(blanks)}) != items.length ({len(items)})")
                else:
                    for k, item in enumerate(items):
                        item_qid = item.get("questionId", "")
                        if k < len(blanks) and blanks[k] != item_qid:
                            errors.append(f"sections[{i}]: blank[{k}] questionId {blanks[k]} != items[{k}].questionId {item_qid}")

        # Choice with item options
        if ptype in TYPES_WITH_ITEM_OPTIONS:
            for j, item in enumerate(items):
                opts = item.get("options", [])
                if len(opts) < 2:
                    errors.append(f"sections[{i}].items[{j}].options must have ≥2 elements")

        # Shared options
        if ptype in TYPES_WITH_SHARED_OPTIONS:
            opts = config.get("options", [])
            if len(opts) < 2:
                errors.append(f"sections[{i}].presentationConfig.options must have ≥2 elements")

        # Matching types
        if ptype in TYPES_REQUIRING_WORD_BANK:
            wb = config.get("wordBank")
            if not isinstance(wb, dict):
                errors.append(f"sections[{i}]: matching type requires wordBank")
            else:
                words = wb.get("words", [])
                if not isinstance(words, list) or len(words) == 0:
                    errors.append(f"sections[{i}].wordBank.words must be a non-empty array")

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

        # Speaking cue_card
        if ptype == "speaking_cue_card":
            if not config.get("topic"):
                errors.append(f"sections[{i}]: speaking_cue_card requires topic")
            bp = config.get("bulletPoints", [])
            if not isinstance(bp, list) or len(bp) == 0:
                errors.append(f"sections[{i}]: speaking_cue_card requires bulletPoints")

    return {"valid": len(errors) == 0, "errors": errors}


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
    if result["valid"]:
        return f"VALID: {path}"
    lines = [f"INVALID: {path} — {len(result['errors'])} error(s):"]
    for err in result["errors"]:
        lines.append(f"  - {err}")
    return "\n".join(lines)


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
        print(validate_transcript(args.file))
    elif args.file.endswith(".json"):
        print(validate_file(args.file))
    else:
        print(validate_transcript(args.file))
