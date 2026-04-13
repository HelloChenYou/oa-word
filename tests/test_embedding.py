from app.services.embedding import build_embedding, cosine_similarity, parse_vector, tokenize_for_embedding, vector_to_pg


def test_build_embedding_is_normalized_and_stable():
    first = build_embedding("手机号应脱敏", dim=16)
    second = build_embedding("手机号应脱敏", dim=16)

    assert first == second
    assert abs(cosine_similarity(first, first) - 1.0) < 0.000001


def test_vector_to_pg_roundtrip():
    vector = build_embedding("OA平台", dim=8)

    assert parse_vector(vector_to_pg(vector)) == vector


def test_tokenize_for_embedding_uses_chinese_bigrams():
    tokens = tokenize_for_embedding("手机号")

    assert "手机" in tokens
    assert "机号" in tokens
