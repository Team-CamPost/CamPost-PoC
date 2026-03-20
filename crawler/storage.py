"""
CamPost Crawler — 스토리지 레이어
 - JSON: PoC 백업용 (로컬 파일)
 - PostgreSQL: 프로덕션 저장소 (asyncpg)
"""

import hashlib
import json
import logging
from pathlib import Path

import asyncpg

from .config import NOTICES_FILE, HASHES_FILE

log = logging.getLogger("campost.storage")


# ── 해시 유틸 ────────────────────────────────────────────

def compute_hash(article_id: str, title: str) -> str:
    """SHA-256(article_id:title) — 중복 수집 방지 키"""
    return hashlib.sha256(f"{article_id}:{title}".encode("utf-8")).hexdigest()


# ── 해시 영속성 ──────────────────────────────────────────

def load_seen_hashes() -> set[str]:
    if HASHES_FILE.exists():
        return set(json.loads(HASHES_FILE.read_text(encoding="utf-8")))
    return set()


def save_seen_hashes(hashes: set[str]) -> None:
    HASHES_FILE.write_text(
        json.dumps(sorted(hashes), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log.debug(f"해시 저장 완료: {len(hashes)}건 → {HASHES_FILE}")


# ── 공지 영속성 ──────────────────────────────────────────

def load_notices() -> list[dict]:
    if NOTICES_FILE.exists():
        return json.loads(NOTICES_FILE.read_text(encoding="utf-8"))
    return []


def save_notices(new_notices: list[dict]) -> None:
    """기존 데이터에 신규 공지를 append하여 저장"""
    existing = load_notices()
    all_notices = existing + new_notices
    NOTICES_FILE.write_text(
        json.dumps(all_notices, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log.info(f"저장 완료: 신규 {len(new_notices)}건 → {NOTICES_FILE} (누적 {len(all_notices)}건)")


# ── PostgreSQL 저장 ───────────────────────────────────────

async def save_notice_to_db(pool: asyncpg.Pool, notice: dict) -> int | None:
    """
    공지사항 1건을 DB에 저장하고 notices.id를 반환.
    이미 존재하면 (article_id 충돌) 기존 id 반환.
    """
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO notices
                    (article_id, title, author, date, category,
                     body_text, source_url, is_pinned, views, hash)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
                ON CONFLICT (article_id) DO UPDATE
                    SET title      = EXCLUDED.title,
                        crawled_at = now()
                RETURNING id
                """,
                notice["article_id"],
                notice["title"],
                notice.get("author", ""),
                notice.get("date", ""),
                notice.get("category", ""),
                notice.get("body_text", ""),
                notice.get("source_url", ""),
                notice.get("is_pinned", False),
                str(notice.get("views", "0")),
                notice["hash"],
            )
            return row["id"]
    except Exception as exc:
        log.error(f"공지 DB 저장 실패 (article_id={notice['article_id']}): {exc}")
        return None


async def save_attachment_to_db(
    pool: asyncpg.Pool, notice_id: int, att: dict
) -> None:
    """
    첨부파일 메타데이터 1건을 DB에 저장.
    file_key 충돌 시 무시 (이미 저장된 파일).
    """
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO attachments
                    (notice_id, file_key, original_name, mime_type,
                     file_size, checksum, source_url, download_ok)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
                ON CONFLICT (file_key) DO NOTHING
                """,
                notice_id,
                att["file_key"],
                att["name"],
                att.get("mime_type", "application/octet-stream"),
                att.get("file_size"),
                att.get("checksum"),
                att.get("url", ""),
                att.get("download_ok", False),
            )
    except Exception as exc:
        log.error(f"첨부파일 DB 저장 실패 (file_key={att.get('file_key')}): {exc}")
