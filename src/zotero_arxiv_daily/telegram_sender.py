#!/usr/bin/env python3
"""Send ArXiv paper recommendations to Telegram."""
import json
import os
import sys
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone


def send_message(bot_token: str, chat_id: str, text: str) -> bool:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    }).encode()
    try:
        with urllib.request.urlopen(url, data=data, timeout=10) as resp:
            return json.loads(resp.read()).get("ok", False)
    except Exception as e:
        print(f"Telegram send error: {e}")
        return False


def escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def format_paper(index: int, total: int, paper: dict) -> str:
    title = escape(paper.get("title", "Unknown"))
    authors = paper.get("authors", [])
    tldr = paper.get("tldr", "") or ""
    url = paper.get("url", "")
    pdf_url = paper.get("pdf_url", "")
    affiliations = paper.get("affiliations") or []
    score = paper.get("score")

    author_str = escape(", ".join(authors[:3]))
    if len(authors) > 3:
        author_str += " et al."

    affil_str = escape(", ".join(affiliations[:2])) if affiliations else ""

    if tldr:
        tldr_short = escape(tldr[:350] + ("..." if len(tldr) > 350 else ""))
    else:
        tldr_short = ""

    lines = [f"<b>[{index}/{total}] {title}</b>"]
    if author_str:
        lines.append(f"👥 {author_str}")
    if affil_str:
        lines.append(f"🏛 {affil_str}")
    if tldr_short:
        lines.append(f"💡 <i>{tldr_short}</i>")
    if score is not None:
        lines.append(f"⭐️ 相关度: {score:.3f}")

    links = []
    if url:
        links.append(f'<a href="{url}">📄 论文</a>')
    if pdf_url:
        links.append(f'<a href="{pdf_url}">📑 PDF</a>')
    if links:
        lines.append(" | ".join(links))

    return "\n".join(lines)


def main():
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    if not bot_token or not chat_id:
        print("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")
        sys.exit(1)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    papers_file = "/tmp/papers.json"

    if not os.path.exists(papers_file):
        send_message(bot_token, chat_id,
            f"📭 <b>ArXiv 日报 {today}</b>\n\n今日没有找到推荐论文（可能是节假日或 arXiv 未更新）。")
        return

    with open(papers_file, encoding="utf-8") as f:
        papers = json.load(f)

    if not papers:
        send_message(bot_token, chat_id,
            f"📭 <b>ArXiv 日报 {today}</b>\n\n今日没有找到推荐论文。")
        return

    total = len(papers)

    # 发送头部消息
    send_message(bot_token, chat_id,
        f"📚 <b>ArXiv 日报 {today}</b>\n\n为你推荐 <b>{total}</b> 篇相关论文，发送中...")

    time.sleep(0.5)

    # 逐篇发送
    for i, paper in enumerate(papers, start=1):
        msg = format_paper(i, total, paper)
        ok = send_message(bot_token, chat_id, msg)
        if not ok:
            print(f"Failed to send paper {i}: {paper.get('title')}")
        time.sleep(0.4)  # 避免触发 Telegram 限速

    # 发送尾部
    send_message(bot_token, chat_id,
        f"✅ 全部 {total} 篇已推送完毕，完整内容请查看邮件。")


if __name__ == "__main__":
    main()



