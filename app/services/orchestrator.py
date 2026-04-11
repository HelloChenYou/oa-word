import asyncio

from app.domain.issues import StoredIssue
from app.logging_utils import elapsed_ms, get_logger, log_info, now_perf
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
    started_at = now_perf()
    chunks = split_text(text)
    all_issues: list[StoredIssue] = []
    total_rule = 0
    total_llm = 0
    llm_rule_pack = _build_rule_pack(owner_id=owner_id)
    log_info(
        logger,
        "proofread_started",
        mode=mode,
        scene=scene,
        owner_id=owner_id,
        chunk_count=len(chunks),
        text_length=len(text),
        has_template=False,
    )

    for idx, chunk in enumerate(chunks):
        rule_issues = check_rules(chunk, owner_id=owner_id)
        llm_issues = await check_with_llm(chunk, mode=mode, scene=scene, rule_pack=llm_rule_pack)
        total_rule += len(rule_issues)
        total_llm += len(llm_issues)
        log_info(
            logger,
            "chunk_processed",
            chunk_index=idx,
            rule_issue_count=len(rule_issues),
            llm_issue_count=len(llm_issues),
            chunk_length=len(chunk),
        )
        all_issues.extend(rule_issues + llm_issues)

    deduped_issues = dedup_issues(all_issues)
    clamped_issues = clamp_issues(deduped_issues)
    log_info(
        logger,
        "proofread_completed",
        rule_issue_total=total_rule,
        llm_issue_total=total_llm,
        before_dedup_count=len(all_issues),
        after_dedup_count=len(deduped_issues),
        after_clamp_count=len(clamped_issues),
        duration_ms=elapsed_ms(started_at),
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
    started_at = now_perf()
    chunks = split_text(text)
    all_issues: list[StoredIssue] = []
    total_rule = 0
    total_llm = 0
    llm_rule_pack = _build_rule_pack(owner_id=owner_id, template_rule_pack=template_rule_pack)
    log_info(
        logger,
        "proofread_started",
        mode=mode,
        scene=scene,
        owner_id=owner_id,
        chunk_count=len(chunks),
        text_length=len(text),
        has_template=True,
    )

    for idx, chunk in enumerate(chunks):
        rule_issues = check_rules(chunk, owner_id=owner_id, template_rule_pack=template_rule_pack)
        llm_issues = await check_with_llm(chunk, mode=mode, scene=scene, rule_pack=llm_rule_pack)
        total_rule += len(rule_issues)
        total_llm += len(llm_issues)
        log_info(
            logger,
            "chunk_processed",
            chunk_index=idx,
            rule_issue_count=len(rule_issues),
            llm_issue_count=len(llm_issues),
            chunk_length=len(chunk),
        )
        all_issues.extend(rule_issues + llm_issues)

    deduped_issues = dedup_issues(all_issues)
    clamped_issues = clamp_issues(deduped_issues)
    log_info(
        logger,
        "proofread_completed",
        rule_issue_total=total_rule,
        llm_issue_total=total_llm,
        before_dedup_count=len(all_issues),
        after_dedup_count=len(deduped_issues),
        after_clamp_count=len(clamped_issues),
        duration_ms=elapsed_ms(started_at),
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
