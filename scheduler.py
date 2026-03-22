"""每日定时调度器（长驻进程模式）"""

import logging
import sys
import time
from datetime import datetime

import pytz
import schedule

from main import load_config, run
from trend_analyzer import analyze_weekly_trend
from mailer import send_trend_email

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _job(config_path: str, tz: "pytz.BaseTzInfo") -> None:
    weekday = datetime.now(tz).weekday()
    if weekday == 6:
        # 周日：发送每周趋势周报
        logger.info("今天是周日，发送每周趋势周报...")
        try:
            config = load_config(config_path)
            trend = analyze_weekly_trend(config)
            send_trend_email(trend, config)
        except Exception as e:
            logger.error("周报发送失败: %s", e, exc_info=True)
    elif weekday == 5:
        # 周六：跳过
        logger.info("今天是周六，跳过推送")
    else:
        # 周一至周五：日常论文推送
        logger.info("定时任务触发，开始执行...")
        try:
            run(config_path)
        except Exception as e:
            logger.error("执行失败: %s", e, exc_info=True)


def main() -> None:
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    config = load_config(config_path)

    sched_cfg = config.get("scheduler", {})
    send_time = sched_cfg.get("send_time", "08:00")
    tz_name = sched_cfg.get("timezone", "Asia/Shanghai")
    tz = pytz.timezone(tz_name)

    logger.info("调度器启动，每日 %s (%s) 发送", send_time, tz_name)

    schedule.every().day.at(send_time, tz).do(_job, config_path=config_path, tz=tz)

    if "--run-now" in sys.argv:
        logger.info("--run-now 参数：立即执行一次")
        _job(config_path, tz)

    while True:
        schedule.run_pending()
        # 显示下次执行时间
        next_run = schedule.next_run()
        if next_run:
            local_next = datetime.fromtimestamp(next_run.timestamp(), tz)
            logger.debug("下次执行: %s", local_next.strftime("%Y-%m-%d %H:%M:%S %Z"))
        time.sleep(30)


if __name__ == "__main__":
    main()
