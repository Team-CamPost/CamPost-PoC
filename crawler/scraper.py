"""
CamPost Crawler — Playwright 기반 스크래퍼
목록 페이지 + 상세 페이지 파싱 담당
"""

import asyncio
import logging
from playwright.async_api import Page

from .config import (
    BASE_URL,
    DETAIL_URL_TEMPLATE,
    SELECTORS,
    PAGE_TIMEOUT,
    SELECTOR_TIMEOUT,
    REQUEST_DELAY,
)

log = logging.getLogger("campost.scraper")


async def fetch_list(page: Page) -> list[dict]:
    """
    공지사항 목록 페이지에서 게시글 기본 정보 추출.

    Returns:
        [
            {
                article_id, title, is_pinned,
                post_number, author, date, views, has_attachment
            },
            ...
        ]
    """
    await page.goto(BASE_URL, wait_until="networkidle", timeout=PAGE_TIMEOUT)
    await page.wait_for_selector(SELECTORS["list_item"], timeout=SELECTOR_TIMEOUT)

    items: list[dict] = await page.evaluate(
        """(sel) => {
            const rows = document.querySelectorAll(sel.list_item);
            const results = [];

            rows.forEach(row => {
                const titleEl = row.querySelector(sel.title_anchor);
                if (!titleEl) return;

                const onclick = titleEl.getAttribute('onclick') || '';
                const idMatch = onclick.match(/viewMessage\\((\\d+)/);
                const articleId = idMatch ? idMatch[1] : null;
                if (!articleId) return;

                const cols = row.querySelectorAll('.dku-list-body-item-col');
                const colTexts = Array.from(cols).map(c => c.textContent.trim());
                const isPinned = !!row.querySelector('.badge-primary');

                results.push({
                    article_id:     articleId,
                    title:          titleEl.getAttribute('title') || titleEl.textContent.trim(),
                    is_pinned:      isPinned,
                    post_number:    isPinned ? null : colTexts[0],
                    author:         colTexts[2] || '',
                    date:           colTexts[3] || '',
                    views:          colTexts[4] || '0',
                    has_attachment: colTexts[5] !== '',
                });
            });

            return results;
        }""",
        SELECTORS,
    )

    log.info(f"목록 수집 완료: {len(items)}건")
    return items


async def fetch_detail(page: Page, article_id: str) -> dict:
    """
    상세 페이지에서 본문·카테고리·첨부파일 추출.

    Returns:
        {body_text, category, attachments: [{name, url, ext}]}
    """
    url = DETAIL_URL_TEMPLATE.format(article_id=article_id)

    try:
        await page.goto(url, wait_until="networkidle", timeout=PAGE_TIMEOUT)
        await page.wait_for_selector(SELECTORS["detail_table"], timeout=10_000)
    except Exception as exc:
        log.warning(f"상세 페이지 로드 실패 (article_id={article_id}): {exc}")
        return {"body_text": "", "category": "", "attachments": []}

    result: dict = await page.evaluate(
        """(sel) => {
            // 본문
            const bodyEl = document.querySelector(sel.body);
            const bodyText = bodyEl ? bodyEl.innerText.trim() : '';

            // 카테고리
            let category = '';
            const rows = document.querySelectorAll('table[summary*="게시판"] tr');
            rows.forEach(row => {
                const th = row.querySelector('th');
                const td = row.querySelector('td');
                if (th && td && th.textContent.includes('분류')) {
                    category = td.textContent.trim();
                }
            });

            // 첨부파일
            const fileLinks = document.querySelectorAll(sel.attachment);
            const attachments = Array.from(fileLinks).map(a => ({
                name: a.textContent.trim(),
                url:  a.href,
                ext:  a.textContent.trim().split('.').pop().toLowerCase(),
            }));

            return { body_text: bodyText, category, attachments };
        }""",
        SELECTORS,
    )

    log.debug(
        f"상세 수집 완료 (article_id={article_id}): "
        f"본문 {len(result['body_text'])}자, 첨부 {len(result['attachments'])}개"
    )
    await asyncio.sleep(REQUEST_DELAY)
    return result
