from __future__ import annotations

import re


def _normalize_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def _extract_overlap(text: str, overlap_chars: int) -> str:
    if overlap_chars <= 0 or len(text) <= overlap_chars:
        return text.strip()

    candidate = text[-overlap_chars:].strip()
    if not candidate:
        return ""

    whitespace_index = candidate.find(" ")
    if whitespace_index > 0:
        candidate = candidate[whitespace_index + 1 :].strip()
    return candidate


def _split_long_text(text: str, *, max_chars: int, overlap_chars: int) -> list[str]:
    chunks: list[str] = []
    start = 0
    text = text.strip()

    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            window = text[start:end]
            min_break = max(int(len(window) * 0.6), 1)
            break_points = [
                window.rfind(marker, min_break)
                for marker in ("\n", ". ", "! ", "? ", "; ", ": ", ", ", " ")
            ]
            best_break = max(break_points)
            if best_break > 0:
                end = start + best_break + 1

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = max(end - overlap_chars, start + 1)

    return chunks


def split_sections(text: str) -> list[tuple[str | None, str]]:
    normalized = _normalize_text(text)
    if not normalized:
        return []

    sections: list[tuple[str | None, str]] = []
    current_heading: str | None = None
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_lines
        body = "\n".join(current_lines).strip()
        if body:
            sections.append((current_heading, body))
        current_lines = []

    for line in normalized.split("\n"):
        markdown_heading = re.match(r"^\s{0,3}#{1,6}\s+(.+?)\s*$", line)
        yaml_heading = re.match(r"^[A-Za-z0-9_\-]+\s*:\s*$", line)

        if markdown_heading:
            flush()
            current_heading = markdown_heading.group(1).strip()
            current_lines.append(line.strip())
            continue

        if yaml_heading and not current_lines:
            current_heading = line.split(":", 1)[0].strip()

        current_lines.append(line)

    flush()

    if not sections:
        return [(None, normalized)]
    return sections


def chunk_text(text: str, *, max_chars: int = 1200, overlap_chars: int = 150) -> list[str]:
    normalized = _normalize_text(text)
    if not normalized:
        return []

    if max_chars <= 0:
        raise ValueError("max_chars must be positive.")
    if overlap_chars < 0:
        raise ValueError("overlap_chars cannot be negative.")

    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", normalized) if paragraph.strip()]
    base_chunks: list[str] = []
    current_parts: list[str] = []

    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            if current_parts:
                base_chunks.append("\n\n".join(current_parts).strip())
                current_parts = []
            base_chunks.extend(
                _split_long_text(paragraph, max_chars=max_chars, overlap_chars=overlap_chars)
            )
            continue

        proposed = "\n\n".join([*current_parts, paragraph]).strip()
        if current_parts and len(proposed) > max_chars:
            base_chunks.append("\n\n".join(current_parts).strip())
            current_parts = [paragraph]
        else:
            current_parts.append(paragraph)

    if current_parts:
        base_chunks.append("\n\n".join(current_parts).strip())

    if overlap_chars <= 0 or len(base_chunks) <= 1:
        return [chunk for chunk in base_chunks if chunk]

    overlapped_chunks: list[str] = []
    for index, chunk in enumerate(base_chunks):
        if index == 0:
            overlapped_chunks.append(chunk)
            continue

        overlap = _extract_overlap(base_chunks[index - 1], overlap_chars)
        if overlap and not chunk.startswith(overlap):
            chunk = f"{overlap}\n\n{chunk}".strip()
        overlapped_chunks.append(chunk)

    return [chunk for chunk in overlapped_chunks if chunk]
