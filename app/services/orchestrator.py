import asyncio

from app.domain.issues import StoredIssue
from app.logging_utils import elapsed_ms, get_logger, log_info, now_perf
from app.services.boundary_guard import clamp_issues
from app.services.chunker import split_text_with_offsets
from app.services.llm_ollama import check_with_llm
from app.services.merger import dedup_issues
from app.services.rule_engine import check_rules
from app.services.rule_repository import build_rule_pack_summary, load_public_rules, load_private_rules, build_template_rules

logger = get_logger(__name__)


def _build_rule_pack(owner_id: str | None, template_rule_pack: str = "{}") -> str:
    rules = load_public_rules() + load_private_rules(owner_id) + build_template_rules(template_rule_pack)
    return build_rule_pack_summary(rules)


def _fill_issue_positions_from_chunk(issues: list[StoredIssue], chunk: str, offset: int) -> list[StoredIssue]:
    """Infer missing issue positions from LLM original_text within the current chunk."""
    search_offsets: dict[str, int] = {}
    positioned: list[StoredIssue] = []
    for issue in issues:
        if issue.position_start is not None and issue.position_end is not None:
            if (
                0 <= issue.position_start <= issue.position_end <= len(chunk)
                and chunk[issue.position_start : issue.position_end] == issue.original_text
            ):
                positioned.append(
                    issue.model_copy(
                        update={
                            "position_start": offset + issue.position_start,
                            "position_end": offset + issue.position_end,
                        }
                    )
                )
                continue
            issue = issue.model_copy(update={"position_start": None, "position_end": None})
        if not issue.original_text:
            positioned.append(issue)
            continue

        local_start = chunk.find(issue.original_text, search_offsets.get(issue.original_text, 0))
        if local_start < 0:
            local_start = chunk.find(issue.original_text)
        if local_start < 0:
            positioned.append(issue)
            continue

        local_end = local_start + len(issue.original_text)
        search_offsets[issue.original_text] = local_end
        positioned.append(
            issue.model_copy(
                update={
                    "position_start": offset + local_start,
                    "position_end": offset + local_end,
                }
            )
        )
    return positioned


def _filter_overexpanded_llm_issues(issues: list[StoredIssue], chunk: str) -> list[StoredIssue]:
    """Drop LLM issues that rewrite a whole sentence for a local replacement."""
    filtered: list[StoredIssue] = []
    for issue in issues:
        if issue.source != "llm":
            filtered.append(issue)
            continue
        if not issue.original_text or not issue.suggested_text:
            filtered.append(issue)
            continue
        original_is_full_chunk = issue.original_text.strip() == chunk.strip()
        suggestion_looks_like_sentence = len(issue.suggested_text) > len(issue.original_text) + 6
        if suggestion_looks_like_sentence and not original_is_full_chunk:
            continue
        filtered.append(issue)
    return filtered


async def run_proofread(text: str, mode: str, scene: str, owner_id: str | None = None) -> list[StoredIssue]:
    started_at = now_perf()
    chunks = split_text_with_offsets(text)
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

    for idx, (chunk, offset) in enumerate(chunks):
        rule_issues = check_rules(chunk, owner_id=owner_id, layer="chunk", offset=offset)
        llm_issues = _fill_issue_positions_from_chunk(
            await check_with_llm(chunk, mode=mode, scene=scene, rule_pack=llm_rule_pack),
            chunk=chunk,
            offset=offset,
        )
        llm_issues = _filter_overexpanded_llm_issues(llm_issues, chunk=chunk)
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

    document_rule_issues = check_rules(text, owner_id=owner_id, layer="document")
    total_rule += len(document_rule_issues)
    all_issues.extend(document_rule_issues)

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
    chunks = split_text_with_offsets(text)
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

    for idx, (chunk, offset) in enumerate(chunks):
        rule_issues = check_rules(chunk, owner_id=owner_id, template_rule_pack=template_rule_pack, layer="chunk", offset=offset)
        llm_issues = _fill_issue_positions_from_chunk(
            await check_with_llm(chunk, mode=mode, scene=scene, rule_pack=llm_rule_pack),
            chunk=chunk,
            offset=offset,
        )
        llm_issues = _filter_overexpanded_llm_issues(llm_issues, chunk=chunk)
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

    document_rule_issues = check_rules(text, owner_id=owner_id, template_rule_pack=template_rule_pack, layer="document")
    total_rule += len(document_rule_issues)
    all_issues.extend(document_rule_issues)

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
