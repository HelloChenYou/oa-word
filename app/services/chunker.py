def split_text(text: str, max_chars: int = 1200, overlap: int = 120) -> list[str]:
    return [chunk for chunk, _ in split_text_with_offsets(text, max_chars=max_chars, overlap=overlap)]


def split_text_with_offsets(text: str, max_chars: int = 1200, overlap: int = 120) -> list[tuple[str, int]]:
    text = text.strip()
    if len(text) <= max_chars:
        return [(text, 0)]

    chunks = []
    start = 0
    n = len(text)

    while start < n:
        end = min(start + max_chars, n)
        chunks.append((text[start:end], start))
        if end == n:
            break
        start = max(0, end - overlap)

    return chunks
