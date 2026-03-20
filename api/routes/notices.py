"""
CamPost API — 공지사항 조회 라우터

GET /api/notices               공지 목록 (페이지네이션)
GET /api/notices/{article_id}  공지 상세 + 첨부파일 목록
"""

from fastapi import APIRouter, HTTPException, Query
from db.database import get_pool

router = APIRouter(prefix="/api/notices", tags=["notices"])


@router.get("")
async def list_notices(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
):
    """공지 목록 반환 (최신순, 페이지네이션)"""
    pool = get_pool()
    offset = (page - 1) * size

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT article_id, title, author, date, category,
                   is_pinned, views, source_url, crawled_at
            FROM notices
            ORDER BY is_pinned DESC, crawled_at DESC
            LIMIT $1 OFFSET $2
            """,
            size,
            offset,
        )
        total = await conn.fetchval("SELECT COUNT(*) FROM notices")

    return {
        "total": total,
        "page": page,
        "size": size,
        "items": [dict(r) for r in rows],
    }


@router.get("/{article_id}")
async def get_notice(article_id: str):
    """공지 상세 + 첨부파일 목록 반환"""
    pool = get_pool()

    async with pool.acquire() as conn:
        notice = await conn.fetchrow(
            """
            SELECT id, article_id, title, author, date, category,
                   body_text, source_url, is_pinned, views, crawled_at
            FROM notices
            WHERE article_id = $1
            """,
            article_id,
        )
        if not notice:
            raise HTTPException(status_code=404, detail="공지를 찾을 수 없습니다")

        attachments = await conn.fetch(
            """
            SELECT file_key, original_name, mime_type, file_size, download_ok
            FROM attachments
            WHERE notice_id = $1 AND download_ok = true
            ORDER BY id
            """,
            notice["id"],
        )

    return {
        **dict(notice),
        "attachments": [dict(a) for a in attachments],
    }
