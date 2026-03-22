"""每周趋势分析：抓取过去7天论文，由 AI 生成热点与趋势报告"""

import logging
from openai import OpenAI
from fetcher import fetch_papers, Paper

logger = logging.getLogger(__name__)

TREND_PROMPT = """\
你是一位 AI 研究领域的专家分析师。以下是过去一周在 {topics} 领域发表的论文列表（标题与摘要）。

请基于这些论文撰写一份**中文周报**，结构如下：

## 本周概览
用2-3句话概括本周整体研究动态。

## 热点研究方向（3-5个）
列出本周最活跃的研究方向，每个方向包含：
- 方向名称
- 简要说明（2-3句）
- 代表性论文标题（1-2篇）

## 值得关注的论文（3-5篇）
挑选本周最具创新性或影响力的论文，每篇包含：
- 标题
- 核心贡献（1-2句）

## 新兴趋势
描述本周出现的新方向或值得持续关注的苗头（2-3点）。

---

论文列表（共 {count} 篇）：
{papers}
"""


def analyze_weekly_trend(config: dict) -> str:
    """抓取过去7天论文并返回 AI 生成的趋势分析 Markdown 文本"""
    # 临时用7天范围抓取
    arxiv_cfg = dict(config["arxiv"])
    arxiv_cfg["days_back"] = 7
    arxiv_cfg["max_results"] = 300

    papers: list[Paper] = fetch_papers(arxiv_cfg)
    if not papers:
        return "本周暂无符合条件的论文。"

    logger.info("周报：共抓取 %d 篇论文，开始 AI 分析...", len(papers))

    # 构造论文列表文本（截断摘要节省 token）
    paper_lines = []
    for i, p in enumerate(papers, 1):
        paper_lines.append(
            f"{i}. 【{p.title}】\n   {p.abstract[:200]}..."
        )
    papers_text = "\n\n".join(paper_lines)

    topics = "、".join(config["arxiv"].get("keywords", ["AI"]))
    prompt = TREND_PROMPT.format(
        topics=topics,
        count=len(papers),
        papers=papers_text,
    )

    llm_cfg = config["llm"]
    client = OpenAI(
        api_key=llm_cfg["api_key"],
        base_url=llm_cfg["base_url"],
        timeout=llm_cfg.get("timeout", 60),
    )

    response = client.chat.completions.create(
        model=llm_cfg["model"],
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000,
    )

    result = response.choices[0].message.content.strip()
    logger.info("周报 AI 分析完成")
    return result
