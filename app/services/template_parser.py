import json
import re
from pathlib import Path

from docx import Document


PLACEHOLDER_PATTERN = re.compile(r"\{([a-zA-Z0-9_]+)\}")
SECTION_PATTERN = re.compile(r"^[一二三四五六七八九十]+、.+$")


def parse_template_text(raw_text: str) -> dict:
    """Extract placeholders and required sections from a template document."""
    placeholders = list(dict.fromkeys(PLACEHOLDER_PATTERN.findall(raw_text)))
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    sections = [line for line in lines if SECTION_PATTERN.match(line)]
    return {
        "placeholders": placeholders,
        "required_sections": list(dict.fromkeys(sections)),
    }


def read_template_content(file_path: Path, file_type: str) -> str:
    if file_type in {"txt", "md"}:
        return file_path.read_text(encoding="utf-8")
    if file_type == "docx":
        doc = Document(str(file_path))
        return "\n".join([paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()])
    raise ValueError(f"unsupported file type: {file_type}")


def parse_template_file(file_path: Path, file_type: str) -> tuple[str, str]:
    raw_text = read_template_content(file_path, file_type)
    parsed = parse_template_text(raw_text)
    return raw_text, json.dumps(parsed, ensure_ascii=False)
