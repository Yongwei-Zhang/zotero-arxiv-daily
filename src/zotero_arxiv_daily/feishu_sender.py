#!/usr/bin/env python3
"""Send ArXiv paper recommendations to Feishu private chat."""
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone

FEISHU_API = "https://open.feishu.cn/open-apis"


def get_token(app_id: str, app_secret: str) -> str:
    url = f"{FEISHU_API}/auth/v3/tenant_access_token/internal"
    data = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read())
        if result.get("code") != 0:
            raise RuntimeError(f"Get token failed: {result}")
        return result["tenant_access_token"]


def send_msg(token: str, open_id: str, msg_type: str, content) -> bool:
    url = f"{FEISHU_API}/im/v1/messages?receive_id_type=open_id"
    payload = json.dumps({
        "receive_id": open_id,
        "msg_type": msg_type,
        "content": json.dumps(content) if msg_type == "interactive" else json.dumps(content),
    }).encode()
    req = urllib.request.Request(url, data=payload, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            if result.get("code") != 0:
                print(f"Send failed: {result}")
            return result.get("code") == 0
    except Exception as e:
        print(f"Send error: {e}")
        return False


def make_paper_card(paper: dict, idx: int, total: int) -> dict:
    title = paper.get("title", "Unknown")
    authors = paper.get("authors", [])
    author_str = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")
    tldr = (paper.get("tldr") or "")
    score = paper.get("score")
    url = paper.get("url", "")
    pdf_url = paper.get("pdf_url", "")

    elements = []
    if author_str:
        elements.append({"tag": "div", "text": {"tag": "lark_md", "content": f"👥 **作者：** {author_str}"}})
    if tldr:
        short = tldr[:400] + ("..." if len(tldr) > 400 else "")
        elements.append({"tag": "div", "text": {"tag": "lark_md", "content": f"💡 **TL;DR：** {short}"}})
    if score is not None:
        elements.append({"tag": "div", "text": {"tag": "lark_md", "content": f"⭐ **相关度：** {score:.3f}"}})

    btns = []
    if url:
        btns.append({"tag": "button", "text": {"tag": "plain_text", "content": "📄 论文主页"}, "url": url, "type": "default"})
    if pdf_url:
        btns.append({"tag": "button", "text": {"tag": "plain_text", "content": "📑 PDF"}, "url": pdf_url, "type": "primary"})
    if btns:
        elements.append({"tag": "action", "actions": btns})

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": f"[{idx}/{total}] {title}"},
            "template": "blue",
        },
        "elements": elements,
    }


def main():
    app_id = os.environ.get("FEISHU_APP_ID", "")
    app_secret = os.environ.get("FEISHU_APP_SECRET", "")
    open_id = os.environ.get("FEISHU_OPEN_ID", "")

    if not all([app_id, app_secret, open_id]):
        print("Missing FEISHU_APP_ID / FEISHU_APP_SECRET / FEISHU_OPEN_ID")
        sys.exit(1)

    token = get_token(app_id, app_secret)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    papers_file = "/tmp/papers.json"
    max_papers = int(os.environ.get("FEISHU_MAX_PAPERS", "20"))

    if not os.path.exists(papers_file):
        send_msg(token, open_id, "text", {"text": f"📭 ArXiv 日报 {today}\n\n今日没有找到推荐论文（节假日或 arXiv 未更新）。"})
        return

    with open(papers_file, encoding="utf-8") as f:
        papers = json.load(f)

    if not papers:
        send_msg(token, open_id, "text", {"text": f"📭 ArXiv 日报 {today}\n\n今日没有找到推荐论文。"})
        return

    papers = papers[:max_papers]
    total = len(papers)

    send_msg(token, open_id, "text", {"text": f"📚 ArXiv 日报 {today}\n\n共推荐 {total} 篇论文，正在发送..."})
    time.sleep(0.5)

    for i, paper in enumerate(papers, start=1):
        ok = send_msg(token, open_id, "interactive", make_paper_card(paper, i, total))
        if not ok:
            print(f"Failed: [{i}] {paper.get('title')}")
        time.sleep(0.5)

    send_msg(token, open_id, "text", {"text": f"✅ 全部 {total} 篇已推送完毕！"})
    print(f"Done: sent {total} papers.")


if __name__ == "__main__":
    main()
