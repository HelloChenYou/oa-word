import asyncio

from app.services.chunker import split_text
from app.services.llm_ollama import check_with_llm
from app.services.merger import dedup_issues
from app.services.rule_engine import check_rules


async def run_proofread(text: str, mode: str, scene: str) -> list[dict]:
    chunks = split_text(text)
    all_issues = []
    total_rule = 0
    total_llm = 0

    for idx, chunk in enumerate(chunks):
        rule_issues = check_rules(chunk)
        llm_issues = await check_with_llm(chunk, mode=mode, scene=scene, rule_pack="{}")
        total_rule += len(rule_issues)
        total_llm += len(llm_issues)
        print(
            f"[CHUNK_ISSUES] idx={idx} rule={len(rule_issues)} llm={len(llm_issues)} "
            f"chunk_len={len(chunk)}"
        )
        all_issues.extend(rule_issues + llm_issues)

    deduped_issues = dedup_issues(all_issues)
    print(
        f"[FINAL_ISSUES] rule_total={total_rule} llm_total={total_llm} "
        f"before_dedup={len(all_issues)} after_dedup={len(deduped_issues)}"
    )
    return deduped_issues


def run_proofread_sync(text: str, mode: str, scene: str) -> list[dict]:
    return asyncio.run(run_proofread(text=text, mode=mode, scene=scene))


async def run_proofread_with_template(text: str, mode: str, scene: str, template_rule_pack: str) -> list[dict]:
    chunks = split_text(text)
    all_issues = []
    total_rule = 0
    total_llm = 0

    for idx, chunk in enumerate(chunks):
        rule_issues = check_rules(chunk)
        llm_issues = await check_with_llm(chunk, mode=mode, scene=scene, rule_pack=template_rule_pack)
        total_rule += len(rule_issues)
        total_llm += len(llm_issues)
        print(
            f"[CHUNK_ISSUES] idx={idx} rule={len(rule_issues)} llm={len(llm_issues)} "
            f"chunk_len={len(chunk)}"
        )
        all_issues.extend(rule_issues + llm_issues)

    deduped_issues = dedup_issues(all_issues)
    print(
        f"[FINAL_ISSUES] rule_total={total_rule} llm_total={total_llm} "
        f"before_dedup={len(all_issues)} after_dedup={len(deduped_issues)}"
    )
    return deduped_issues


def run_proofread_with_template_sync(text: str, mode: str, scene: str, template_rule_pack: str) -> list[dict]:
    return asyncio.run(
        run_proofread_with_template(text=text, mode=mode, scene=scene, template_rule_pack=template_rule_pack)
    )
