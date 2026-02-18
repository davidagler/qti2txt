import html
import logging
import re

import html2text

try:
    from mathml_to_latex import MathMLToLaTeX
except Exception:  # pragma: no cover - optional import safety
    MathMLToLaTeX = None

logger = logging.getLogger(__name__)

_IMG_MATHML_PATTERN = re.compile(
    r"<img\b[^>]*\bdata-mathml\s*=\s*(?P<quote>[\"'])(?P<mathml>.*?)(?P=quote)[^>]*>",
    flags=re.IGNORECASE | re.DOTALL,
)


# Clean up HTML
def html_to_cleantext(html_text):
    if html_text is None:
        return ""
    if not isinstance(html_text, str):
        html_text = str(html_text)

    html_text = _replace_mathml_images_with_latex(html_text)

    h = html2text.HTML2Text()
    h.ignore_links = False
    h.body_width = 0
    h.single_line_break = True
    clean_text = h.handle(html_text)  # convert
    if clean_text is None:
        return ""
    clean_text = re.sub(r"\s+", " ", clean_text)  # remove extra spaces
    clean_text = _cleanup_markdown_artifacts(clean_text)
    return clean_text


def _replace_mathml_images_with_latex(html_text):
    """Replace Wiris/Canvas data-mathml image tags with inline LaTeX."""
    if "data-mathml" not in html_text:
        return html_text

    def replace_img(match):
        raw_mathml = match.group("mathml")
        latex = _convert_canvas_mathml_to_latex(raw_mathml)
        if not latex:
            return match.group(0)
        return f"${latex}$"

    updated_text = _IMG_MATHML_PATTERN.sub(replace_img, html_text)
    if updated_text != html_text:
        return updated_text

    # Some exports may preserve escaped HTML tags in text fields.
    if "&lt;img" in html_text:
        unescaped_text = html.unescape(html_text)
        return _IMG_MATHML_PATTERN.sub(replace_img, unescaped_text)

    return html_text


def _convert_canvas_mathml_to_latex(raw_mathml):
    """Normalize Canvas-escaped MathML and convert it to LaTeX."""
    if not raw_mathml or MathMLToLaTeX is None:
        return None

    normalized_mathml = html.unescape(raw_mathml)
    normalized_mathml = (
        normalized_mathml.replace("«", "<").replace("»", ">").replace("¨", '"')
    )
    normalized_mathml = normalized_mathml.replace("§", "&")

    try:
        latex = MathMLToLaTeX.convert(normalized_mathml)
    except Exception as exc:
        logger.warning("Could not convert data-mathml to LaTeX: %s", exc)
        return None

    if not latex:
        return None

    return latex.strip()


def _cleanup_markdown_artifacts(text):
    """
    Clean frequent html2text artifacts from Canvas exports:
    - escaped periods in numbered tokens (e.g., 1\\.)
    - orphan emphasis markers at end of text (e.g., ____)
    """
    text = text.rstrip()

    # html2text sometimes emits escaped list punctuation (e.g., 1\.)
    text = re.sub(r"(?<=\d)\\\.(?=\s|$)", ".", text)

    # Remove trailing emphasis marker runs with no paired opening marker.
    text = re.sub(r"[_*]{2,}\s*$", "", text)
    text = re.sub(r"(?<![A-Za-z0-9])[_*]\s*$", "", text)
    text = re.sub(r"[_*]{2,}(?=[.!?]\s*$)", "", text)
    text = re.sub(r"(?<![A-Za-z0-9])[_*](?=[.!?]\s*$)", "", text)
    text = re.sub(r"\s+([.,;:?])", r"\1", text)

    return text.rstrip()


# Renumber text file
def renumber_file(file_path):
    with open(file_path, "r") as file:
        lines = file.readlines()

    new_lines = []
    question_number = 1

    for line in lines:
        # Match lines that start with a number followed by a period and a space
        if re.match(r"^\d+\.\s", line):
            new_line = re.sub(r"^\d+\.\s", f"{question_number}. ", line)
            new_lines.append(new_line)
            question_number += 1
        else:
            new_lines.append(line)

    with open(file_path, "w") as file:
        file.writelines(new_lines)
