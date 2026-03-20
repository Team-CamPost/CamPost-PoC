"""
CamPost — asyncpg 연결 풀 관리
앱 시작 시 init_pool(), 종료 시 close_pool() 호출.
"""

import asyncpg

from crawler.config import DB_DSN

_pool: asyncpg.Pool | None = None


async def init_pool() -> None:
    global _pool
    _pool = await asyncpg.create_pool(
        dsn=DB_DSN,
        min_size=2,
        max_size=10,
        command_timeout=30,
    )


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("DB 풀이 초기화되지 않았습니다. init_pool()을 먼저 호출하세요.")
    return _pool
