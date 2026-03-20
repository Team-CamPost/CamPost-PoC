"""
CamPost Crawler — 설정 관리
환경변수(.env) 또는 기본값으로 동작
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── 크롤링 대상 ──────────────────────────────────────────
BASE_URL = "https://cms.dankook.ac.kr/web/sw/-1"

DETAIL_URL_TEMPLATE = (
    "https://cms.dankook.ac.kr/web/sw/-1"
    "?p_p_id=dku_bbs_web_BbsPortlet"
    "&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view"
    "&_dku_bbs_web_BbsPortlet_cur=1"
    "&_dku_bbs_web_BbsPortlet_action=view_message"
    "&_dku_bbs_web_BbsPortlet_orderBy=createDate"
    "&_dku_bbs_web_BbsPortlet_bbsMessageId={article_id}"
)

USER_AGENT = (
    "Mozilla/5.0 (compatible; CamPost-Crawler/1.0; +https://campost.dku.ac.kr/bot)"
)

# ── 스케줄러 ─────────────────────────────────────────────
CRAWL_INTERVAL_MINUTES: int = int(os.getenv("CRAWL_INTERVAL_MINUTES", "60"))

# ── Playwright ───────────────────────────────────────────
HEADLESS: bool = os.getenv("HEADLESS", "true").lower() != "false"
PAGE_TIMEOUT: int = 30_000   # ms
SELECTOR_TIMEOUT: int = 15_000  # ms
REQUEST_DELAY: float = 1.0   # 게시글 간 대기 (초)

# ── 저장 경로 ────────────────────────────────────────────
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./data"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

NOTICES_FILE = OUTPUT_DIR / "collected_notices.json"
HASHES_FILE = OUTPUT_DIR / "seen_hashes.json"

FILES_DIR = OUTPUT_DIR / "files"
FILES_DIR.mkdir(parents=True, exist_ok=True)

# 텍스트 추출 대상 확장자
EXTRACTABLE_EXTS = {"pdf", "hwp", "hwpx"}

# ── 데이터베이스 ─────────────────────────────────────────
DB_DSN: str = os.getenv(
    "DATABASE_URL",
    "postgresql://campost:campost@localhost:5432/campost",
)

# ── DOM 셀렉터 (PoC 검증 완료) ───────────────────────────
SELECTORS = {
    "list_item": ".dku-list-body-item:not(.header)",
    "title_anchor": ".item-title h4 a",
    "detail_table": 'table[summary*="게시판"]',
    "body": "td.r_cont",
    "attachment": 'a[href*="download=true"]',
}
