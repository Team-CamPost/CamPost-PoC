-- CamPost DB 스키마
-- 실행: psql -U campost -d campost -f db/schema.sql

-- ── 공지사항 테이블 ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS notices (
    id          BIGSERIAL    PRIMARY KEY,
    article_id  VARCHAR(20)  NOT NULL UNIQUE,   -- 단국대 게시글 ID
    title       TEXT         NOT NULL,
    author      VARCHAR(100),
    date        VARCHAR(20),                    -- 원본 날짜 문자열 (예: "2026.03.10")
    category    VARCHAR(50),
    body_text   TEXT,
    source_url  TEXT,                           -- 단국대 원문 링크
    is_pinned   BOOLEAN      DEFAULT false,
    views       VARCHAR(20),
    hash        CHAR(64)     NOT NULL,          -- SHA-256(article_id:title)
    crawled_at  TIMESTAMPTZ  DEFAULT now()
);

-- ── 첨부파일 테이블 ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS attachments (
    id            BIGSERIAL    PRIMARY KEY,
    notice_id     BIGINT       NOT NULL REFERENCES notices(id) ON DELETE CASCADE,
    file_key      VARCHAR(255) NOT NULL UNIQUE, -- 서버 저장 파일명 (서빙 식별자)
    original_name VARCHAR(255) NOT NULL,        -- 사용자에게 보여줄 원본 파일명
    mime_type     VARCHAR(100),
    file_size     BIGINT,
    checksum      CHAR(64),                     -- SHA-256 hex (무결성 검증)
    source_url    TEXT,                         -- 단국대 원본 다운로드 URL
    download_ok   BOOLEAN      DEFAULT false,
    created_at    TIMESTAMPTZ  DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_attachments_notice_id ON attachments(notice_id);
CREATE INDEX IF NOT EXISTS idx_notices_article_id    ON notices(article_id);
