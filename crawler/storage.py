"""
CamPost Crawler — 로컬 파일 스토리지
Phase 0 PoC 단계: JSON 파일 기반 저장
Sprint 1 이후 PostgreSQL로 교체 예정
"""

import hashlib
import json
import logging
from pathlib import Path

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
