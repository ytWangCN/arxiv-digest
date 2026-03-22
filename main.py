"""主入口：执行一次完整的抓取 → 推荐 → 发送流程"""

import logging
import sys

import yaml

from fetcher import fetch_papers
from recommender import Recommender
from mailer import send_email

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def load_config(path: str = "config.yaml") -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def run(config_path: str = "config.yaml") -> None:
    config = load_config(config_path)

    # 1. 抓取论文
    papers = fetch_papers(config["arxiv"])
    if not papers:
        logger.info("今日没有符合条件的论文，跳过发送")
        return

    # 2. 大模型推荐（可选）
    rec_cfg = config.get("recommender", {})
    if rec_cfg.get("enabled", False):
        recommender = Recommender(config["llm"])
        papers = recommender.score_papers(papers, rec_cfg)
        if not papers:
            logger.info("所有论文评分低于阈值，跳过发送")
            return

    # 3. 发送邮件
    send_email(papers, config)
    logger.info("完成！共推送 %d 篇论文", len(papers))


if __name__ == "__main__":
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    run(config_path)
