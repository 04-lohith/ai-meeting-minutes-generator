"""
utils.py — Helper utilities for the AI Meeting Minutes Generator.

Provides JSON serialisation, PDF generation, and timestamp formatting.
"""

import json
import os
import datetime

from fpdf import FPDF


def save_json(data: dict, path: str = "outputs/meeting_minutes.json") -> str:
    """Save meeting minutes dict to a JSON file.

    Returns:
        The absolute path of the written file.
    """
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return os.path.abspath(path)


def generate_pdf(data: dict, path: str = "outputs/meeting_minutes.pdf") -> str:
    """Create a nicely formatted PDF from the meeting minutes dict.

    Returns:
        The absolute path of the written PDF.
    """
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # ── Title ───────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(33, 37, 41)
    pdf.cell(0, 14, "Meeting Minutes", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(2)

    # Timestamp
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(108, 117, 125)
    pdf.cell(
        0, 8,
        f"Generated on {format_timestamp()}",
        new_x="LMARGIN", new_y="NEXT", align="C",
    )
    pdf.ln(6)

    # ── Divider ─────────────────────────────────────────────────
    pdf.set_draw_color(206, 212, 218)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(6)

    # ── Summary ─────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(33, 37, 41)
    pdf.cell(0, 10, "Summary", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(52, 58, 64)
    pdf.multi_cell(0, 7, data.get("summary", "N/A"))
    pdf.ln(6)

    # ── Action Items ────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(33, 37, 41)
    pdf.cell(0, 10, "Action Items", new_x="LMARGIN", new_y="NEXT")

    action_items = data.get("action_items", [])
    if action_items:
        # Table header
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_fill_color(233, 236, 239)
        pdf.cell(45, 8, "Person", border=1, fill=True)
        pdf.cell(100, 8, "Task", border=1, fill=True)
        pdf.cell(45, 8, "Deadline", border=1, fill=True,
                 new_x="LMARGIN", new_y="NEXT")

        # Table rows
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(52, 58, 64)
        for item in action_items:
            pdf.cell(45, 8, str(item.get("person", "")), border=1)
            pdf.cell(100, 8, str(item.get("task", "")), border=1)
            pdf.cell(45, 8, str(item.get("deadline", "")), border=1,
                     new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 8, "No action items recorded.", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # ── Decisions ───────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(33, 37, 41)
    pdf.cell(0, 10, "Decisions", new_x="LMARGIN", new_y="NEXT")

    decisions = data.get("decisions", [])
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(52, 58, 64)
    if decisions:
        for decision in decisions:
            pdf.cell(6, 7, chr(8226))  # bullet
            pdf.multi_cell(0, 7, f"  {decision}")
    else:
        pdf.cell(0, 8, "No decisions recorded.", new_x="LMARGIN", new_y="NEXT")

    pdf.output(path)
    return os.path.abspath(path)


def format_timestamp() -> str:
    """Return a human-readable timestamp for the current moment."""
    return datetime.datetime.now().strftime("%B %d, %Y at %I:%M %p")


def minutes_to_text(data: dict) -> str:
    """Convert meeting minutes dict to a plain-text representation."""
    lines = [
        "MEETING MINUTES",
        f"Generated: {format_timestamp()}",
        "",
        "=" * 50,
        "SUMMARY",
        "=" * 50,
        data.get("summary", "N/A"),
        "",
        "=" * 50,
        "ACTION ITEMS",
        "=" * 50,
    ]
    for item in data.get("action_items", []):
        lines.append(
            f"  • {item.get('person', '?')}: "
            f"{item.get('task', '?')} "
            f"(Deadline: {item.get('deadline', 'Not specified')})"
        )
    lines.extend([
        "",
        "=" * 50,
        "DECISIONS",
        "=" * 50,
    ])
    for decision in data.get("decisions", []):
        lines.append(f"  • {decision}")

    return "\n".join(lines)
