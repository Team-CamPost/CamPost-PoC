# CamPost 크롤링 아키텍처

> 최종 작성일: 2026.03.20

---

## 전체 흐름

```
main.py (진입점)
    │
    ├─ APScheduler (60분마다 반복 실행)
    │
    └─ run_crawler()
         │
         ├─ [1단계] scraper.fetch_list()               ← 목록 페이지 파싱
         │
         ├─ [2단계] storage.compute_hash()             ← 중복 공지 필터링
         │
         ├─ [3단계] scraper.fetch_detail()             ← 상세 페이지 파싱
         │
         ├─ [4단계] file_handler.process_attachments() ← 파일 처리
         │
         └─ [5단계] storage.save_*()                   ← JSON + DB 저장
```

---

## 핵심 기술: Playwright (헤드리스 브라우저)

단국대 공지사항 페이지는 **JavaScript로 렌더링**되기 때문에 일반 HTTP 요청(`requests`, `httpx`)으로는 내용을 가져올 수 없습니다.

| 방식 | 결과 |
|------|------|
| 일반 HTTP 요청 | HTML에 빈 `<div>` 만 존재 (JS 미실행) |
| Playwright | 실제 브라우저처럼 JS 실행 후 완성된 DOM 읽음 |

Playwright가 **Chromium 브라우저를 백그라운드(headless)에서 실행**하여 실제 사람이 접속하는 것처럼 동작합니다.

---

## 단계별 상세 설명

### 1단계 — 목록 수집 (`scraper.fetch_list`)

```
Playwright → cms.dankook.ac.kr/web/sw/-1 접속
           → JS 렌더링 완료 대기 (networkidle)
           → DOM에서 공지 행(.dku-list-body-item) 전체 추출
           → page.evaluate()로 각 행에서 데이터 파싱
```

**추출 데이터:**

| 필드 | 추출 위치 |
|------|-----------|
| `article_id` | `onclick="viewMessage(168882)"` 에서 정규식 추출 |
| `title` | `<h4 a title="...">` 속성 |
| `author` | 컬럼 텍스트 |
| `date` | 컬럼 텍스트 |
| `views` | 컬럼 텍스트 |
| `is_pinned` | `.badge-primary` 요소 존재 여부 |
| `has_attachment` | 첨부파일 컬럼 텍스트 여부 |

---

### 2단계 — 중복 필터링 (`storage.compute_hash`)

```
SHA-256(article_id + ":" + title)
    → seen_hashes.json 과 비교
    → 이미 있으면 → SKIP
    → 없으면     → 다음 단계 진행
```

새 공지만 골라내는 관문 역할로, **매번 전체 사이트를 다시 저장하지 않도록** 합니다.

---

### 3단계 — 상세 수집 (`scraper.fetch_detail`)

```
Playwright → 상세 URL 접속
              (?p_p_id=dku_bbs_web_BbsPortlet
               &action=view_message
               &bbsMessageId={article_id})
           → table[summary*="게시판"] 로딩 대기
           → 본문, 분류, 첨부파일 링크 추출
```

**추출 데이터:**

| 필드 | 추출 위치 |
|------|-----------|
| `body_text` | `td.r_cont` 의 `innerText` 전체 |
| `category` | `<th>분류</th>` 인접 `<td>` 값 |
| `attachments` | `a[href*="download=true"]` 전체 → name, url, ext |

게시글 간 요청 사이에 **1초 딜레이**를 두어 서버에 무리를 주지 않습니다.

---

### 4단계 — 첨부파일 처리 (`file_handler.process_attachments`)

```
각 첨부파일 URL에 대해:

  ① 다운로드
     httpx (비동기)
         → 단국대 서버에 GET 요청 (follow_redirects=True)
         → 파일 바이너리 수신
         → data/files/{article_id}_{파일명} 으로 저장

  ② 텍스트 추출 (AI 요약 준비용)
     PDF  → pdfplumber : 각 페이지 텍스트 추출
     HWP  → olefile    : PrvText 스트림 읽기 (UTF-16LE 디코딩)
     HWPX → zipfile    : Contents/section*.xml 파싱 (한컴 네임스페이스)

  ③ 메타데이터 계산
     checksum  → SHA-256 (파일 전체, 64자 hex)
     file_size → 저장된 파일 바이트 수
     mime_type → 확장자 기반 MIME 타입
```

**지원 파일 형식:**

| 확장자 | 처리 방식 | 텍스트 추출 |
|--------|-----------|------------|
| `.pdf` | pdfplumber | ✅ |
| `.hwp` | olefile (PrvText 스트림) | ✅ |
| `.hwpx` | zipfile + XML 파싱 | ✅ |
| `.zip` `.png` `.jpg` 등 | 다운로드만 | ❌ (AI 요약 제외) |

---

### 5단계 — 저장 (`storage`)

```
JSON (백업)
  → data/collected_notices.json 에 append 저장

PostgreSQL (프로덕션)
  → notices    테이블 INSERT  (ON CONFLICT article_id → UPDATE)
  → attachments 테이블 INSERT (ON CONFLICT file_key  → NOTHING)
```

---

## 모듈 책임 요약

```
DKU_Caps/
│
├── main.py                  전체 오케스트레이션 + APScheduler
├── demo.py                  수집 결과 확인용 로컬 웹서버 (port 9090)
│
├── crawler/
│   ├── config.py            URL, DOM 셀렉터, 경로, DB 설정값 관리
│   ├── scraper.py           Playwright 조작, DOM 파싱 (HTML → dict)
│   ├── file_handler.py      httpx 다운로드, PDF/HWP 텍스트 추출, 메타데이터
│   └── storage.py           해시 중복체크, JSON / PostgreSQL 저장
│
├── db/
│   ├── database.py          asyncpg 연결 풀 (init / close / get)
│   └── schema.sql           notices, attachments 테이블 정의
│
├── api/
│   ├── main.py              FastAPI 앱 (lifespan DB 연결)
│   └── routes/
│       ├── notices.py       GET /api/notices, /api/notices/{article_id}
│       └── files.py         GET /api/files/{file_key} (스트리밍 다운로드)
│
└── data/
    ├── collected_notices.json   수집된 공지사항 (JSON 백업)
    ├── seen_hashes.json         중복 방지 해시 목록
    └── files/                   다운로드된 첨부파일
```

---

## 데이터 흐름 다이어그램

```
[단국대 홈페이지]
      │
      │  Playwright (Chromium headless)
      │  - 목록 페이지 렌더링
      │  - 상세 페이지 렌더링
      ▼
[scraper.py]
      │  dict 리스트 반환
      │  {article_id, title, author, date, ...}
      │  {body_text, category, attachments: [{name, url, ext}]}
      ▼
[storage.compute_hash]
      │  신규 공지만 통과
      ▼
[file_handler.py]
      │  httpx 비동기 다운로드
      │  pdfplumber / olefile / zipfile 텍스트 추출
      │  SHA-256 체크섬 계산
      ▼
[data/files/]              ← 실제 파일 저장
      │
      ▼
[storage.py]
      ├─→ data/collected_notices.json   (JSON 백업)
      └─→ PostgreSQL
              notices 테이블
              attachments 테이블
                    │
                    ▼
             [api/routes/]
             GET /api/notices/{id}
             GET /api/files/{file_key}  → 파일 스트리밍
                    │
                    ▼
             [프론트엔드]
             공지 목록 / 상세 / 첨부파일 다운로드
```

---

## 한 줄 요약

> **Playwright로 JS 렌더링된 단국대 공지 페이지를 실제 브라우저처럼 접속 → DOM 파싱으로 공지 데이터 추출 → httpx로 첨부파일 다운로드 → pdfplumber/olefile로 텍스트 추출 → PostgreSQL + JSON에 저장 → 60분마다 자동 반복**
