import hashlib
import math
import re

from app.config import settings


def tokenize_for_embedding(text: str) -> list[str]:
    terms = re.findall(r"[\u4e00-\u9fffA-Za-z0-9_]{1,}", text)
    tokens: list[str] = []
    for term in terms:
        if re.fullmatch(r"[\u4e00-\u9fff]+", term):
            tokens.extend(term[index : index + 2] for index in range(max(len(term) - 1, 1)))
        else:
            tokens.append(term.lower())
    return [token for token in tokens if token]


def build_embedding(text: str, dim: int | None = None) -> list[float]:
    size = dim or settings.rag_vector_dim
    vector = [0.0] * size
    for token in tokenize_for_embedding(text):
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        bucket = int.from_bytes(digest[:4], "big") % size
        sign = 1.0 if int.from_bytes(digest[4:], "big") % 2 == 0 else -1.0
        vector[bucket] += sign

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def vector_to_pg(value: list[float]) -> str:
    return "[" + ",".join(f"{item:.8f}" for item in value) + "]"


def parse_vector(value) -> list[float]:
    if value is None:
        return []
    if isinstance(value, list):
        return [float(item) for item in value]
    text = str(value).strip()
    if not text:
        return []
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    return [float(item.strip()) for item in text.split(",") if item.strip()]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right))
