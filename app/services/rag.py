import re
from dataclasses import dataclass
from types import SimpleNamespace

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal
from app.models import KnowledgeChunk, KnowledgeDocument
from app.services.embedding import build_embedding, cosine_similarity, parse_vector, vector_to_pg


@dataclass(frozen=True)
class RagHit:
    chunk_index: int
    document_id: str
    document_name: str
    knowledge_chunk_index: int
    score: float
    content_preview: str


def split_knowledge_text(text: str, max_chars: int | None = None) -> list[str]:
    max_len = max_chars or settings.rag_chunk_chars
    paragraphs = [item.strip() for item in re.split(r"\n+", text) if item.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if not current:
            current = paragraph
            continue
        if len(current) + 1 + len(paragraph) <= max_len:
            current = f"{current}\n{paragraph}"
        else:
            chunks.extend(_split_long_chunk(current, max_len))
            current = paragraph
    if current:
        chunks.extend(_split_long_chunk(current, max_len))
    return chunks


def _split_long_chunk(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    return [text[start : start + max_chars] for start in range(0, len(text), max_chars)]


def replace_document_chunks(db: Session, document_id: str, raw_text: str) -> int:
    db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.document_id == document_id))
    chunks = split_knowledge_text(raw_text)
    for index, content in enumerate(chunks):
        db.add(
            KnowledgeChunk(
                document_id=document_id,
                chunk_index=index,
                content=content,
                embedding=vector_to_pg(build_embedding(content)),
            )
        )
    return len(chunks)


def _query_terms(query: str) -> list[str]:
    terms = [item for item in re.findall(r"[\u4e00-\u9fffA-Za-z0-9_]{2,}", query) if item.strip()]
    return list(dict.fromkeys(terms))


def _score_chunk(content: str, terms: list[str]) -> int:
    if not terms:
        return 0
    score = 0
    for term in terms:
        score += content.count(term) * max(len(term), 1)
    return score


def search_knowledge_chunks(query: str, top_k: int | None = None) -> list[tuple[KnowledgeDocument, KnowledgeChunk, float]]:
    if not settings.rag_enabled:
        return []
    limit = top_k or settings.rag_top_k
    terms = _query_terms(query)
    query_embedding = build_embedding(query)
    if not terms and not any(query_embedding):
        return []

    db = SessionLocal()
    try:
        if db.bind is not None and db.bind.dialect.name == "postgresql" and settings.rag_retrieval_mode in {"vector", "hybrid"}:
            vector_hits = _search_by_pgvector(db=db, query=query, query_embedding=query_embedding, top_k=limit)
            if vector_hits or settings.rag_retrieval_mode == "vector":
                return vector_hits

        rows = (
            db.execute(
                select(KnowledgeDocument, KnowledgeChunk)
                .join(KnowledgeChunk, KnowledgeChunk.document_id == KnowledgeDocument.id)
                .where(KnowledgeDocument.enabled.is_(True))
            )
            .all()
        )
        scored = [
            (document, chunk, score)
            for document, chunk in rows
            if (score := _score_chunk(chunk.content, terms)) > 0
        ]
        if settings.rag_retrieval_mode in {"vector", "hybrid"}:
            scored.extend(
                (document, chunk, cosine_similarity(query_embedding, parse_vector(chunk.embedding)))
                for document, chunk in rows
                if chunk.embedding
            )
        scored.sort(key=lambda item: (-item[2], item[0].created_at, item[1].chunk_index))
        return _dedup_hits(scored)[:limit]
    finally:
        db.close()


def _search_by_pgvector(
    db: Session,
    query: str,
    query_embedding: list[float],
    top_k: int,
) -> list[tuple[KnowledgeDocument, KnowledgeChunk, float]]:
    terms = _query_terms(query)
    keyword_case = " + ".join([f"(length(c.content) - length(replace(c.content, :term_{idx}, ''))) / greatest(length(:term_{idx}), 1)" for idx, _ in enumerate(terms)])
    keyword_expr = keyword_case if keyword_case else "0"
    params = {f"term_{idx}": term for idx, term in enumerate(terms)}
    params.update(
        {
            "embedding": vector_to_pg(query_embedding),
            "top_k": top_k,
            "vector_weight": settings.rag_vector_weight,
            "keyword_weight": 1.0 - settings.rag_vector_weight,
        }
    )
    rows = db.execute(
        text(
            f"""
            SELECT
                d.id AS document_id,
                d.name AS document_name,
                d.doc_type AS doc_type,
                d.file_type AS file_type,
                d.file_path AS file_path,
                d.raw_text AS raw_text,
                d.enabled AS enabled,
                d.created_at AS document_created_at,
                c.id AS chunk_id,
                c.chunk_index AS chunk_index,
                c.content AS content,
                c.embedding AS embedding,
                c.created_at AS chunk_created_at,
                (
                    :vector_weight * (1 - (c.embedding <=> CAST(:embedding AS vector)))
                    + :keyword_weight * ({keyword_expr})
                ) AS score
            FROM knowledge_chunks c
            JOIN knowledge_documents d ON d.id = c.document_id
            WHERE d.enabled = true AND c.embedding IS NOT NULL
            ORDER BY score DESC, d.created_at ASC, c.chunk_index ASC
            LIMIT :top_k
            """
        ),
        params,
    ).mappings().all()
    hits = []
    for row in rows:
        document = SimpleNamespace(
            id=row["document_id"],
            name=row["document_name"],
            doc_type=row["doc_type"],
            file_type=row["file_type"],
            file_path=row["file_path"],
            raw_text=row["raw_text"],
            enabled=row["enabled"],
            created_at=row["document_created_at"],
        )
        chunk = SimpleNamespace(
            id=row["chunk_id"],
            document_id=row["document_id"],
            chunk_index=row["chunk_index"],
            content=row["content"],
            embedding=row["embedding"],
            created_at=row["chunk_created_at"],
        )
        hits.append((document, chunk, float(row["score"] or 0.0)))
    return hits


def _dedup_hits(scored: list[tuple[KnowledgeDocument, KnowledgeChunk, float]]) -> list[tuple[KnowledgeDocument, KnowledgeChunk, float]]:
    seen = set()
    result = []
    for document, chunk, score in scored:
        key = (document.id, chunk.chunk_index)
        if key in seen:
            continue
        seen.add(key)
        result.append((document, chunk, score))
    return result


def build_rag_context(query: str, top_k: int | None = None) -> str:
    context, _ = build_rag_context_with_hits(query=query, chunk_index=0, top_k=top_k)
    return context


def build_rag_context_with_hits(query: str, chunk_index: int, top_k: int | None = None) -> tuple[str, list[RagHit]]:
    hits = search_knowledge_chunks(query=query, top_k=top_k)
    if not hits:
        return "无", []
    blocks = []
    rag_hits: list[RagHit] = []
    for index, (document, chunk, score) in enumerate(hits, start=1):
        content_preview = chunk.content[:500]
        blocks.append(
            "\n".join(
                [
                    f"[{index}] document_id={document.id}",
                    f"name={document.name}",
                    f"chunk_index={chunk.chunk_index}",
                    f"score={score}",
                    f"content={chunk.content}",
                ]
            )
        )
        rag_hits.append(
            RagHit(
                chunk_index=chunk_index,
                document_id=document.id,
                document_name=document.name,
                knowledge_chunk_index=chunk.chunk_index,
                score=float(score),
                content_preview=content_preview,
            )
        )
    return "\n\n".join(blocks), rag_hits


def count_document_chunks(db: Session, document_id: str) -> int:
    count = db.scalar(select(func.count()).select_from(KnowledgeChunk).where(KnowledgeChunk.document_id == document_id))
    return int(count or 0)
