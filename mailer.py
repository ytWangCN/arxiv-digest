"""生成 HTML 邮件并通过 Gmail SMTP 发送"""

import smtplib
import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from fetcher import Paper

logger = logging.getLogger(__name__)

SCORE_COLOR = {
    range(9, 11): "#16a34a",   # 绿色：9-10
    range(7, 9): "#2563eb",    # 蓝色：7-8
    range(1, 7): "#6b7280",    # 灰色：1-6
}


def _score_badge(score: int) -> str:
    if score == 0:
        return ""
    color = "#6b7280"
    for r, c in SCORE_COLOR.items():
        if score in r:
            color = c
            break
    return (
        f'<span style="background:{color};color:#fff;padding:2px 8px;'
        f'border-radius:12px;font-size:12px;font-weight:bold;">{score}/10</span>'
    )


def _paper_card(paper: Paper, index: int, with_score: bool) -> str:
    authors = ", ".join(paper.authors[:3])
    if len(paper.authors) > 3:
        authors += " et al."
    date_str = paper.published.strftime("%Y-%m-%d")
    cats = " · ".join(paper.categories[:3])

    score_html = f"&nbsp;{_score_badge(paper.score)}" if with_score and paper.score else ""
    reason_html = (
        f'<p style="color:#6b7280;font-size:13px;margin:4px 0 0 0;">'
        f'<b>推荐理由：</b>{paper.score_reason}</p>'
        if paper.score_reason else ""
    )
    summary_html = (
        f'<p style="color:#374151;font-size:13px;margin:6px 0 0 0;'
        f'background:#f9fafb;padding:8px;border-radius:6px;">'
        f'<b>中文摘要：</b>{paper.summary_zh}</p>'
        if paper.summary_zh else ""
    )

    return f"""
    <div style="border:1px solid #e5e7eb;border-radius:10px;padding:16px;
                margin-bottom:16px;background:#ffffff;">
      <div style="display:flex;align-items:baseline;gap:8px;">
        <span style="color:#9ca3af;font-size:13px;min-width:24px;">{index}.</span>
        <div style="flex:1;">
          <a href="{paper.url}" style="color:#1d4ed8;font-size:15px;font-weight:600;
             text-decoration:none;line-height:1.4;">{paper.title}</a>
          {score_html}
          <p style="color:#6b7280;font-size:12px;margin:4px 0 0 0;">
            {authors} &nbsp;·&nbsp; {date_str} &nbsp;·&nbsp;
            <span style="color:#7c3aed;">{cats}</span>
          </p>
          <p style="color:#4b5563;font-size:13px;margin:8px 0 0 0;line-height:1.6;">
            {paper.abstract[:300]}...
          </p>
          {reason_html}
          {summary_html}
          <p style="margin:8px 0 0 0;">
            <a href="{paper.pdf_url}" style="color:#dc2626;font-size:12px;
               text-decoration:none;border:1px solid #fca5a5;padding:2px 8px;
               border-radius:4px;">PDF</a>
            &nbsp;
            <a href="{paper.url}" style="color:#2563eb;font-size:12px;
               text-decoration:none;border:1px solid #93c5fd;padding:2px 8px;
               border-radius:4px;">Abstract</a>
          </p>
        </div>
      </div>
    </div>
    """


def build_html(papers: list[Paper], with_score: bool, date_str: str) -> str:
    cards = "".join(_paper_card(p, i + 1, with_score) for i, p in enumerate(papers))
    score_note = (
        '<p style="color:#6b7280;font-size:13px;margin:0 0 16px 0;">'
        '论文已按推荐评分从高到低排列，仅展示达到阈值的论文。</p>'
        if with_score else ""
    )
    return f"""
    <!DOCTYPE html>
    <html lang="zh">
    <head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
    <body style="margin:0;padding:0;background:#f3f4f6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
      <div style="max-width:700px;margin:32px auto;padding:0 16px;">
        <div style="background:#1e3a8a;padding:24px 28px;border-radius:12px 12px 0 0;">
          <h1 style="color:#ffffff;margin:0;font-size:22px;">
            arxiv 每日论文摘要
          </h1>
          <p style="color:#93c5fd;margin:6px 0 0 0;font-size:14px;">{date_str} &nbsp;·&nbsp; 共 {len(papers)} 篇</p>
        </div>
        <div style="background:#f9fafb;padding:20px 28px;border-radius:0 0 12px 12px;">
          {score_note}
          {cards if papers else '<p style="color:#6b7280;">今日没有符合条件的论文。</p>'}
        </div>
        <p style="text-align:center;color:#9ca3af;font-size:12px;margin-top:16px;">
          由 arxiv-digest 自动生成 · <a href="https://arxiv.org" style="color:#9ca3af;">arxiv.org</a>
        </p>
      </div>
    </body>
    </html>
    """


def send_trend_email(trend_md: str, config: dict) -> None:
    """发送每周趋势周报邮件"""
    import re

    email_cfg = config["email"]
    from datetime import datetime, timedelta
    today = datetime.now()
    week_start = (today - timedelta(days=6)).strftime("%m/%d")
    week_end = today.strftime("%m/%d")
    date_label = f"{today.year}年 {week_start}–{week_end}"
    subject = f"arxiv 周报 {date_label} | 研究趋势分析"

    # 将 Markdown 转为简单 HTML
    def md_to_html(md: str) -> str:
        lines = md.split("\n")
        html_lines = []
        for line in lines:
            if line.startswith("## "):
                html_lines.append(f'<h2 style="color:#1e3a8a;margin:24px 0 8px;font-size:17px;border-bottom:2px solid #dbeafe;padding-bottom:6px;">{line[3:]}</h2>')
            elif line.startswith("### "):
                html_lines.append(f'<h3 style="color:#1d4ed8;margin:16px 0 4px;font-size:15px;">{line[4:]}</h3>')
            elif re.match(r"^[-•] ", line):
                html_lines.append(f'<li style="margin:4px 0;color:#374151;">{line[2:]}</li>')
            elif line.strip() == "---":
                html_lines.append('<hr style="border:none;border-top:1px solid #e5e7eb;margin:20px 0;">')
            elif line.strip() == "":
                html_lines.append("<br>")
            else:
                # 处理加粗
                line = re.sub(r"\*\*(.+?)\*\*", r'<b>\1</b>', line)
                html_lines.append(f'<p style="margin:4px 0;color:#374151;line-height:1.7;">{line}</p>')
        return "\n".join(html_lines)

    body_html = md_to_html(trend_md)
    html = f"""
    <!DOCTYPE html>
    <html lang="zh">
    <head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
    <body style="margin:0;padding:0;background:#f3f4f6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
      <div style="max-width:700px;margin:32px auto;padding:0 16px;">
        <div style="background:linear-gradient(135deg,#1e3a8a,#7c3aed);padding:24px 28px;border-radius:12px 12px 0 0;">
          <h1 style="color:#ffffff;margin:0;font-size:22px;">arxiv 周报</h1>
          <p style="color:#c4b5fd;margin:6px 0 0 0;font-size:14px;">{date_label} &nbsp;·&nbsp; Robot Learning &amp; World Model</p>
        </div>
        <div style="background:#ffffff;padding:24px 28px;border-radius:0 0 12px 12px;">
          {body_html}
        </div>
        <p style="text-align:center;color:#9ca3af;font-size:12px;margin-top:16px;">
          由 arxiv-digest 自动生成 · <a href="https://arxiv.org" style="color:#9ca3af;">arxiv.org</a>
        </p>
      </div>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = email_cfg["sender"]
    msg["To"] = ", ".join(email_cfg["recipients"])
    msg.attach(MIMEText(html, "html", "utf-8"))

    logger.info("发送周报至 %s ...", email_cfg["recipients"])
    try:
        with smtplib.SMTP_SSL(email_cfg["smtp_server"], 465) as server:
            server.login(email_cfg["sender"], email_cfg["app_password"])
            server.sendmail(email_cfg["sender"], email_cfg["recipients"], msg.as_bytes())
    except Exception:
        with smtplib.SMTP(email_cfg["smtp_server"], email_cfg["smtp_port"]) as server:
            server.ehlo()
            server.starttls()
            server.login(email_cfg["sender"], email_cfg["app_password"])
            server.sendmail(email_cfg["sender"], email_cfg["recipients"], msg.as_bytes())
    logger.info("周报发送成功")


def send_email(papers: list[Paper], config: dict) -> None:
    email_cfg = config["email"]
    rec_enabled = config.get("recommender", {}).get("enabled", False)
    date_str = datetime.now().strftime("%Y年%m月%d日")

    html = build_html(papers, with_score=rec_enabled, date_str=date_str)
    subject = f"arxiv 每日摘要 {date_str}（{len(papers)} 篇）"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = email_cfg["sender"]
    msg["To"] = ", ".join(email_cfg["recipients"])
    msg.attach(MIMEText(html, "html", "utf-8"))

    logger.info("发送邮件至 %s ...", email_cfg["recipients"])
    # 优先尝试 SSL（465），fallback 到 STARTTLS（587）
    try:
        with smtplib.SMTP_SSL(email_cfg["smtp_server"], 465) as server:
            server.login(email_cfg["sender"], email_cfg["app_password"])
            server.sendmail(email_cfg["sender"], email_cfg["recipients"], msg.as_bytes())
    except Exception:
        with smtplib.SMTP(email_cfg["smtp_server"], email_cfg["smtp_port"]) as server:
            server.ehlo()
            server.starttls()
            server.login(email_cfg["sender"], email_cfg["app_password"])
            server.sendmail(email_cfg["sender"], email_cfg["recipients"], msg.as_bytes())
    logger.info("邮件发送成功")
