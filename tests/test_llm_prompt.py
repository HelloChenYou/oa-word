from app.services.llm_ollama import build_user_prompt


def test_build_user_prompt_includes_rag_context():
    prompt = build_user_prompt(
        chunk="请上报手机号13800138000。",
        mode="review",
        scene="general",
        rule_pack='{"rules":[]}',
        rag_context="[1] name=公文规范\ncontent=手机号应脱敏。",
    )

    assert "[检索到的知识库片段]" in prompt
    assert "手机号应脱敏" in prompt
    assert "请上报手机号13800138000" in prompt
