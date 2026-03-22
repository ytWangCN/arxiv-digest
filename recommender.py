"""使用大模型对论文进行评分与中文摘要生成"""

import json
import logging
import concurrent.futures

from openai import OpenAI

from fetcher import Paper

logger = logging.getLogger(__name__)

SCORE_PROMPT = """\
你是一位 AI 研究助手。请根据以下研究兴趣对论文打分（1-10），并提供简短理由和中文摘要。

研究兴趣：{interests}

论文标题：{title}
论文摘要：{abstract}

请严格以 JSON 格式返回，不要包含其他内容：
{{
  "score": <整数 1-10>,
  "reason": "<一句话说明打分理由，英文>",
  "summary_zh": "<2-3 句中文摘要，说明论文核心贡献>"
}}
"""


class Recommender:
    def __init__(self, llm_config: dict):
        self.client = OpenAI(
            api_key=llm_config["api_key"],
            base_url=llm_config["base_url"],
            timeout=llm_config.get("timeout", 30),
        )
        self.model = llm_config["model"]

    def _score_one(self, paper: Paper, interests: str) -> Paper:
        """对单篇论文评分，出错时跳过（保留原始默认值）"""
        try:
            prompt = SCORE_PROMPT.format(
                interests=interests,
                title=paper.title,
                abstract=paper.abstract[:800],
            )
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            data = json.loads(response.choices[0].message.content)
            paper.score = int(data.get("score", 0))
            paper.score_reason = data.get("reason", "")
            paper.summary_zh = data.get("summary_zh", "")
        except Exception as e:
            logger.warning("论文 %s 评分失败: %s", paper.arxiv_id, e)
        return paper

    def score_papers(
        self,
        papers: list[Paper],
        rec_config: dict,
    ) -> list[Paper]:
        """并发评分所有论文，返回达到阈值的列表（按分数降序）"""
        interests = rec_config.get("interests", "")
        threshold = rec_config.get("score_threshold", 6)
        concurrency = rec_config.get("concurrency", 3)

        logger.info("开始评分 %d 篇论文（并发=%d）...", len(papers), concurrency)

        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = [pool.submit(self._score_one, p, interests) for p in papers]
            scored = [f.result() for f in concurrent.futures.as_completed(futures)]

        # 过滤低分，按分数降序
        filtered = sorted(
            [p for p in scored if p.score >= threshold],
            key=lambda p: p.score,
            reverse=True,
        )
        logger.info("评分完成，%d 篇论文达到阈值 %d", len(filtered), threshold)
        return filtered
