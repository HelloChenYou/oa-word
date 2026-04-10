import asyncio

from app.domain.issues import StoredIssue
from app.logging_utils import get_logger
from app.services.boundary_guard import clamp_issues
from app.services.chunker import split_text
from app.services.llm_ollama import check_with_llm
from app.services.merger import dedup_issues
from app.services.rule_engine import check_rules
from app.services.rule_repository import build_rule_pack_summary, load_public_rules, load_private_rules, build_template_rules

logger = get_logger(__name__)


def _build_rule_pack(owner_id: str | None, template_rule_pack: str = "{}") -> str:
    rules = load_public_rules() + load_private_rules(owner_id) + build_template_rules(template_rule_pack)
    return build_rule_pack_summary(rules)


async def run_proofread(text: str, mode: str, scene: str, owner_id: str | None = None) -> list[StoredIssue]:
    chunks = split_text(text)
    all_issues: list[StoredIssue] = []
    total_rule = 0
    total_llm = 0
    llm_rule_pack = _build_rule_pack(owner_id=owner_id)

    for idx, chunk in enumerate(chunks):
        rule_issues = check_rules(chunk, owner_id=owner_id)
        llm_issues = await check_with_llm(chunk, mode=mode, scene=scene, rule_pack=llm_rule_pack)
        total_rule += len(rule_issues)
        total_llm += len(llm_issues)
        logger.info(
            "[CHUNK_ISSUES] idx=%s rule=%s llm=%s chunk_len=%s",
            idx,
            len(rule_issues),
            len(llm_issues),
            len(chunk),
        )
        all_issues.extend(rule_issues + llm_issues)

    deduped_issues = dedup_issues(all_issues)
    clamped_issues = clamp_issues(deduped_issues)
    logger.info(
        "[FINAL_ISSUES] rule_total=%s llm_total=%s before_dedup=%s after_dedup=%s after_clamp=%s",
        total_rule,
        total_llm,
        len(all_issues),
        len(deduped_issues),
        len(clamped_issues),
    )
    return clamped_issues


def run_proofread_sync(text: str, mode: str, scene: str, owner_id: str | None = None) -> list[StoredIssue]:
    return asyncio.run(run_proofread(text=text, mode=mode, scene=scene, owner_id=owner_id))


async def run_proofread_with_template(
    text: str,
    mode: str,
    scene: str,
    template_rule_pack: str,
    owner_id: str | None = None,
) -> list[StoredIssue]:
    chunks = split_text(text)
    all_issues: list[StoredIssue] = []
    total_rule = 0
    total_llm = 0
    llm_rule_pack = _build_rule_pack(owner_id=owner_id, template_rule_pack=template_rule_pack)

    for idx, chunk in enumerate(chunks):
        rule_issues = check_rules(chunk, owner_id=owner_id, template_rule_pack=template_rule_pack)
        llm_issues = await check_with_llm(chunk, mode=mode, scene=scene, rule_pack=llm_rule_pack)
        total_rule += len(rule_issues)
        total_llm += len(llm_issues)
        logger.info(
            "[CHUNK_ISSUES] idx=%s rule=%s llm=%s chunk_len=%s",
            idx,
            len(rule_issues),
            len(llm_issues),
            len(chunk),
        )
        all_issues.extend(rule_issues + llm_issues)

    deduped_issues = dedup_issues(all_issues)
    clamped_issues = clamp_issues(deduped_issues)
    logger.info(
        "[FINAL_ISSUES] rule_total=%s llm_total=%s before_dedup=%s after_dedup=%s after_clamp=%s",
        total_rule,
        total_llm,
        len(all_issues),
        len(deduped_issues),
        len(clamped_issues),
    )
    return clamped_issues


def run_proofread_with_template_sync(
    text: str,
    mode: str,
    scene: str,
    template_rule_pack: str,
    owner_id: str | None = None,
) -> list[StoredIssue]:
    return asyncio.run(
        run_proofread_with_template(
            text=text,
            mode=mode,
            scene=scene,
            template_rule_pack=template_rule_pack,
            owner_id=owner_id,
        )
    )
