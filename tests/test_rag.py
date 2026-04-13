from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.services import rag
from app.services.embedding import build_embedding, parse_vector


def test_split_knowledge_text_keeps_paragraphs_when_possible():
    chunks = rag.split_knowledge_text("第一段规范。\n\n第二段规范。", max_chars=20)
    assert chunks == ["第一段规范。\n第二段规范。"]


def test_split_knowledge_text_splits_long_chunks():
    chunks = rag.split_knowledge_text("abcdef", max_chars=2)
    assert chunks == ["ab", "cd", "ef"]


def test_build_rag_context_formats_search_hits(monkeypatch):
    document = SimpleNamespace(id="kb_1", name="公文规范")
    chunk = SimpleNamespace(chunk_index=0, content="手机号应进行脱敏处理。")
    monkeypatch.setattr(rag, "search_knowledge_chunks", lambda query, top_k=None: [(document, chunk, 8)])

    context = rag.build_rag_context("手机号13800138000")

    assert "document_id=kb_1" in context
    assert "name=公文规范" in context
    assert "手机号应进行脱敏处理。" in context


def test_build_rag_context_returns_traceable_hits(monkeypatch):
    document = SimpleNamespace(id="kb_1", name="公文规范")
    chunk = SimpleNamespace(chunk_index=2, content="手机号应进行脱敏处理。")
    monkeypatch.setattr(rag, "search_knowledge_chunks", lambda query, top_k=None: [(document, chunk, 0.8)])

    context, hits = rag.build_rag_context_with_hits("手机号13800138000", chunk_index=3)

    assert "document_id=kb_1" in context
    assert hits[0].chunk_index == 3
    assert hits[0].document_id == "kb_1"
    assert hits[0].knowledge_chunk_index == 2
    assert hits[0].score == 0.8


def test_replace_document_chunks_stores_embeddings():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = session_factory()
    try:
        chunk_count = rag.replace_document_chunks(db, document_id="kb_1", raw_text="手机号应脱敏。")
        db.commit()
        rows = db.query(rag.KnowledgeChunk).all()
        assert chunk_count == 1
        assert parse_vector(rows[0].embedding)
    finally:
        db.close()


def test_vector_fallback_can_score_semantically_related_chunk(monkeypatch):
    document = SimpleNamespace(id="kb_1", name="规范", created_at=0)
    related = SimpleNamespace(chunk_index=0, content="手机号应脱敏", embedding=rag.vector_to_pg(build_embedding("手机号应脱敏")))
    unrelated = SimpleNamespace(chunk_index=1, content="模板章节说明", embedding=rag.vector_to_pg(build_embedding("模板章节说明")))
    query_embedding = build_embedding("员工手机号码")

    scored = [
        (document, related, rag.cosine_similarity(query_embedding, parse_vector(related.embedding))),
        (document, unrelated, rag.cosine_similarity(query_embedding, parse_vector(unrelated.embedding))),
    ]
    scored.sort(key=lambda item: -item[2])

    assert scored[0][1].content == "手机号应脱敏"
