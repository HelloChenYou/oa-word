def split_text(text: str, max_chars: int = 1200, overlap: int = 120) -> list[str]:
    text = text.strip()
    if len(text) <= max_chars:
        return [text]

    chunks = []
    start = 0
    n = len(text)

    while start < n:
        end = min(start + max_chars, n)
        chunks.append(text[start:end])
        if end == n:
            break
        start = max(0, end - overlap)

    return chunks
