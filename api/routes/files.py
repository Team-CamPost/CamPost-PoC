"""
CamPost API — 첨부파일 다운로드 라우터

GET /api/files/{file_key}  파일 스트리밍 다운로드
"""

import urllib.parse
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from crawler.config import FILES_DIR
from db.database import get_pool

router = APIRouter(prefix="/api/files", tags=["files"])

_FILES_DIR_RESOLVED = FILES_DIR.resolve()


@router.get("/{file_key:path}")
async def download_file(file_key: str):
    """
    file_key로 첨부파일을 스트리밍 다운로드.

    보안:
      - DB에 등록된 file_key만 허용 (임의 경로 접근 차단)
      - Path Traversal 방지: resolve()로 FILES_DIR 내부인지 검증
      - Content-Disposition: filename*=UTF-8'' 로 한글 파일명 안전 전달
    """
    pool = get_pool()

    # 1. DB에서 파일 메타데이터 조회
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT original_name, mime_type
            FROM attachments
            WHERE file_key = $1 AND download_ok = true
            """,
            file_key,
        )

    if not row:
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")

    # 2. 실제 파일 경로 확인 + Path Traversal 방지
    file_path = (FILES_DIR / file_key).resolve()
    if not str(file_path).startswith(str(_FILES_DIR_RESOLVED)):
        raise HTTPException(status_code=400, detail="잘못된 파일 경로입니다")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="파일이 서버에 존재하지 않습니다")

    # 3. 한글 파일명 RFC 5987 인코딩 후 스트리밍 반환
    encoded_name = urllib.parse.quote(row["original_name"])
    mime = row["mime_type"] or "application/octet-stream"

    return FileResponse(
        path=file_path,
        media_type=mime,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}",
            "X-Content-Type-Options": "nosniff",
        },
    )
