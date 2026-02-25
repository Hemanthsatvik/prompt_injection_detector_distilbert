def chunk_text(text: str, chunk_size: int) -> list[str]:
    """
    Split text into chunks at word boundaries.

    Args:
        text: The text to chunk
        chunk_size: Maximum characters per chunk (must be positive)

    Returns:
        Array of text chunks
    """
    if chunk_size <= 0:
        raise ValueError(f"chunk_size must be positive, got {chunk_size}")

    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        # Find word boundary (don't split mid-word)
        if end < len(text):
            last_space = text.rfind(" ", start, end)
            if last_space > start:
                end = last_space
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end

    return chunks
