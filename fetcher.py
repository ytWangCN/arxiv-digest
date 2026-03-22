"""从 arxiv 抓取论文"""

import logging
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass

import arxiv

logger = logging.getLogger(__name__)


@dataclass
class Paper:
    arxiv_id: str
    title: str
    authors: list[str]
    abstract: str
    url: str
    pdf_url: str
    published: datetime
    categories: list[str]
    # 由推荐模块填充
    score: int = 0
    score_reason: str = ""
    summary_zh: str = ""


def fetch_papers(arxiv_config: dict) -> list[Paper]:
    """把关键词和分类都交给 arxiv 服务端过滤，本地只做日期裁剪"""
    categories = arxiv_config["categories"]
    keywords = arxiv_config.get("keywords", [])
    max_results = arxiv_config.get("max_results", 200)
    days_back = arxiv_config.get("days_back", 1)

    # 分类子句：(cat:cs.AI OR cat:cs.CV OR ...)
    cat_clause = " OR ".join(f"cat:{c}" for c in categories)

    # 关键词子句（标题或摘要命中任意一个）：(ti:kw1 OR abs:kw1 OR ti:kw2 OR ...)
    if keywords:
        kw_parts = []
        for kw in keywords:
            kw_parts.append(f'ti:"{kw}"')
            kw_parts.append(f'abs:"{kw}"')
        kw_clause = " OR ".join(kw_parts)
        query = f"({cat_clause}) AND ({kw_clause})"
    else:
        query = cat_clause

    logger.info("查询 arxiv: %s", query)

    client = arxiv.Client(page_size=100, delay_seconds=1, num_retries=3)
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )

    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    results: list[Paper] = []

    for r in client.results(search):
        if r.published < cutoff:
            break
        results.append(
            Paper(
                arxiv_id=r.entry_id.split("/")[-1],
                title=r.title.strip().replace("\n", " "),
                authors=[a.name for a in r.authors],
                abstract=r.summary.strip().replace("\n", " "),
                url=r.entry_id,
                pdf_url=r.pdf_url,
                published=r.published,
                categories=[c for c in r.categories],
            )
        )

    logger.info("筛选后共 %d 篇论文", len(results))
    return results
