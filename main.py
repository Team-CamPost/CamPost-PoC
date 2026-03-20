"""
CamPost Crawler — 진입점
단국대 소프트웨어학과 공지사항 자동 수집기

실행 방법:
    pip install -r requirements.txt
    playwright install chromium
    python main.py
"""

import asyncio
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from playwright.async_api import async_playwright

from crawler.config import CRAWL_INTERVAL_MINUTES, HEADLESS, USER_AGENT
from crawler.scraper import fetch_list, fetch_detail
from crawler.file_handler import process_attachments
from crawler.storage import (
    compute_hash,
    load_seen_hashes,
    save_seen_hashes,
    save_notices,
    save_notice_to_db,
    save_attachment_to_db,
)
from db.database import init_pool, close_pool, get_pool

# ── 로거 설정 ────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("campost")


# ── 핵심 크롤링 로직 ─────────────────────────────────────

async def run_crawler() -> None:
    log.info("=" * 60)
    log.info(f"크롤링 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info("=" * 60)

    seen_hashes = load_seen_hashes()
    collected: list[dict] = []
    skip_count = 0

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=HEADLESS)
            context = await browser.new_context(user_agent=USER_AGENT)
            page = await context.new_page()

            # ── 1단계: 목록 수집 ──────────────────────────
            log.info("[1/3] 공지사항 목록 수집 중...")
            list_items = await fetch_list(page)

            # ── 2단계: 신규 항목 상세 수집 ────────────────
            log.info("[2/3] 신규 게시글 상세 수집 중...")
            for item in list_items:
                h = compute_hash(item["article_id"], item["title"])

                if h in seen_hashes:
                    log.info(f"  [SKIP] {item['title'][:40]}")
                    skip_count += 1
                    continue

                log.info(f"  [NEW]  {item['title'][:50]}")
                detail = await fetch_detail(page, item["article_id"])

                # ── 첨부파일 다운로드 + 텍스트 추출 ────────
                if detail["attachments"]:
                    log.info(f"  [FILE] 첨부파일 {len(detail['attachments'])}개 처리 중...")
                    detail["attachments"] = await process_attachments(
                        detail["attachments"], item["article_id"]
                    )

                notice = {
                    **item,
                    **detail,
                    "source_url": (
                        f"https://cms.dankook.ac.kr/web/sw/-1"
                        f"?p_p_id=dku_bbs_web_BbsPortlet"
                        f"&_dku_bbs_web_BbsPortlet_action=view_message"
                        f"&_dku_bbs_web_BbsPortlet_bbsMessageId={item['article_id']}"
                    ),
                    "hash": h,
                    "crawled_at": datetime.now().isoformat(),
                }
                collected.append(notice)
                seen_hashes.add(h)

            await browser.close()

    except Exception as exc:
        log.error(f"크롤링 중 오류 발생: {exc}", exc_info=True)

    # ── 3단계: 결과 저장 ──────────────────────────────────
    log.info("[3/4] 결과 저장 중...")
    save_seen_hashes(seen_hashes)

    if collected:
        save_notices(collected)          # JSON 백업
        await _save_to_db(collected)     # PostgreSQL
        _print_preview(collected)
    else:
        log.info(f"신규 게시글 없음 (건너뜀 {skip_count}건)")

    log.info("크롤링 완료")


async def _save_to_db(notices: list[dict]) -> None:
    """수집된 공지사항 목록을 PostgreSQL에 저장"""
    try:
        pool = get_pool()
    except RuntimeError:
        log.warning("DB 풀 미초기화 — PostgreSQL 저장 건너뜀")
        return

    for notice in notices:
        notice_id = await save_notice_to_db(pool, notice)
        if notice_id is None:
            continue
        for att in notice.get("attachments", []):
            if att.get("download_ok") and att.get("file_key"):
                await save_attachment_to_db(pool, notice_id, att)

    log.info(f"DB 저장 완료: {len(notices)}건")


def _print_preview(notices: list[dict]) -> None:
    log.info(f"\n▼ 수집 결과 미리보기 ({len(notices)}건)")
    for n in notices:
        log.info("  " + "─" * 50)
        log.info(f"  제목   : {n['title']}")
        log.info(f"  날짜   : {n['date']}  |  분류: {n.get('category', '—')}")
        log.info(f"  본문   : {n['body_text'][:80].replace(chr(10), ' ')}...")
        log.info(f"  첨부   : {len(n['attachments'])}개")
        for att in n["attachments"]:
            log.info(f"    [{att['ext'].upper()}] {att['name']}")
        log.info(f"  해시   : {n['hash'][:16]}...")


# ── 스케줄러 진입점 ──────────────────────────────────────

async def main() -> None:
    # DB 풀 초기화
    try:
        await init_pool()
        log.info("PostgreSQL 연결 풀 초기화 완료")
    except Exception as exc:
        log.warning(f"PostgreSQL 연결 실패 ({exc}) — JSON 모드로 계속 진행")

    # 즉시 1회 실행
    await run_crawler()

    # 이후 매 N분마다 반복
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_crawler,
        trigger="interval",
        minutes=CRAWL_INTERVAL_MINUTES,
        id="campost_crawler",
        name="단국대 SW학과 공지 수집",
        misfire_grace_time=300,
    )
    scheduler.start()
    log.info(f"스케줄러 시작: {CRAWL_INTERVAL_MINUTES}분마다 자동 수집 (Ctrl+C로 종료)")

    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        await close_pool()
        log.info("스케줄러 정상 종료")


if __name__ == "__main__":
    asyncio.run(main())
