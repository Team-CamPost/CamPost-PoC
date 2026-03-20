# pip install playwright
# playwright install

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from typing import List, Tuple
from playwright.sync_api import sync_playwright


TARGET_URL = "https://cms.dankook.ac.kr/web/sw/-1?p_p_id=dku_bbs_web_BbsPortlet&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view&_dku_bbs_web_BbsPortlet_cur=1&_dku_bbs_web_BbsPortlet_action=view_message&_dku_bbs_web_BbsPortlet_orderBy=createDate&_dku_bbs_web_BbsPortlet_bbsMessageId=166348"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)


DATE_PATTERN = re.compile(r"\b\d{4}[./-]\d{2}[./-]\d{2}\b")


def normalize_to_board_list_url(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query, keep_blank_values=True)

    action_key = "_dku_bbs_web_BbsPortlet_action"
    message_id_key = "_dku_bbs_web_BbsPortlet_bbsMessageId"

    if action_key in query and query[action_key]:
        query[action_key] = ["view"]

    query.pop(message_id_key, None)

    new_query = urlencode(query, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


def pick_date_from_row_text(row_text: str) -> str:
    match = DATE_PATTERN.search(row_text)
    if match:
        return match.group(0)
    return ""


def crawl_notice_titles_and_dates(url: str, limit: int = 5) -> List[Tuple[str, str]]:
    results: List[Tuple[str, str]] = []
    target_url = normalize_to_board_list_url(url)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=USER_AGENT, locale="ko-KR")
        page = context.new_page()

        page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1500)

        # 단국대 CMS 학과공지 + 일반 게시판 대응 후보 셀렉터
        row_selectors = [
            ".dku-list-body .dku-list-body-item",
            "#main-content table tbody tr",
            "div.portlet-body table tbody tr",
            ".bbs_list table tbody tr",
            "table tbody tr",
            ".board-list tbody tr",
            ".list_table tbody tr",
            "ul.board-list li",
        ]

        rows = []
        for selector in row_selectors:
            rows = page.query_selector_all(selector)
            if rows:
                break

        for row in rows:
            title = ""
            date = ""

            title_selectors = [
                ".item-title a",
                "td.left a",
                "td.subject a",
                "td.title a",
                "td a",
                "a",
                ".title",
            ]
            date_selectors = [
                ".dku-list-body-item-col:nth-child(4)",
                "td.date",
                "td:nth-last-child(1)",
                "td:nth-child(4)",
                ".date",
                "span.date",
            ]

            for sel in title_selectors:
                node = row.query_selector(sel)
                if node:
                    title = (node.inner_text() or "").strip()
                    if title:
                        break

            for sel in date_selectors:
                node = row.query_selector(sel)
                if node:
                    date = (node.inner_text() or "").strip()
                    if date:
                        break

            # 날짜 셀렉터에서 못 찾으면 행 전체 텍스트에서 추출
            if not date:
                row_text = (row.inner_text() or "").strip()
                date = pick_date_from_row_text(row_text)

            if title:
                # 헤더/빈 값/불필요 링크 필터링
                if title in {"제목", "공지", "작성자", "조회수", "날짜"}:
                    continue
                if "학과공지" in title and "공지" == title.strip():
                    continue
                results.append((title, date))

            if len(results) >= limit:
                break

        context.close()
        browser.close()

    return results


def main() -> None:
    notices = crawl_notice_titles_and_dates(TARGET_URL, limit=5)

    if not notices:
        print("공지사항을 찾지 못했습니다. TARGET_URL 또는 셀렉터를 확인하세요.")
        return

    print("[크롤링 결과 - 제목 5개]")
    for idx, (title, date) in enumerate(notices, start=1):
        print(f"{idx}. {title} | 날짜: {date or 'N/A'}")


if __name__ == "__main__":
    main()
