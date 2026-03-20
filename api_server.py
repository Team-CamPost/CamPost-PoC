# pip install fastapi "uvicorn[standard]" pydantic

from __future__ import annotations

import os
import smtplib
from pathlib import Path
from typing import Any

from email.message import EmailMessage
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from crawling_test import TARGET_URL, crawl_notice_titles_and_dates
from parsing_test import extract_hwp_text_with_hwp5txt, extract_pdf_text, is_text_readable


app = FastAPI(title="Major-Flow PoC API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CrawlRequest(BaseModel):
    url: str = TARGET_URL
    limit: int = Field(default=5, ge=1, le=30)


class ParseRequest(BaseModel):
    hwpPath: str = "test.hwp"
    pdfPath: str = "봉사활동인증서_플로깅.pdf"


class SmtpRequest(BaseModel):
    smtpServer: str | None = None
    smtpPort: int | None = None
    smtpUser: str | None = None
    smtpPassword: str | None = None
    toEmail: str | None = None
    subject: str = "[PoC] SMTP 테스트 메일"
    body: str = "학교 SMTP 서버를 통한 메일 발송 테스트입니다."
    allowedDomain: str = "dankook.ac.kr"
    allowExternalRecipient: bool = False


def _load_env_default(key: str, fallback: str = "") -> str:
    return os.getenv(key, fallback)


def _preview(text: str, length: int = 220) -> str:
    return text[:length]


def _validate_recipient_domain(recipient: str, domain: str, allow_external: bool) -> None:
    if allow_external:
        return
    if not recipient.lower().endswith(f"@{domain}"):
        raise ValueError(f"수신자는 @{domain} 도메인만 허용됩니다.")


def _send_mail(req: SmtpRequest) -> None:
    smtp_server = req.smtpServer or _load_env_default("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = req.smtpPort or int(_load_env_default("SMTP_PORT", "587"))
    smtp_user = req.smtpUser or _load_env_default("SMTP_USER", "")
    smtp_password = req.smtpPassword or _load_env_default("SMTP_PASSWORD", "")
    to_email = req.toEmail or _load_env_default("TO_EMAIL", "")

    if not smtp_user or not smtp_password or not to_email:
        raise ValueError("SMTP_USER, SMTP_PASSWORD, TO_EMAIL 값이 필요합니다.")

    _validate_recipient_domain(to_email, req.allowedDomain, req.allowExternalRecipient)

    msg = EmailMessage()
    msg["From"] = smtp_user
    msg["To"] = to_email
    msg["Subject"] = req.subject
    msg.set_content(req.body)

    if smtp_port == 587:
        with smtplib.SMTP(smtp_server, smtp_port, timeout=20) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
    elif smtp_port == 465:
        with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=20) as server:
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
    else:
        raise ValueError("SMTP_PORT는 587 또는 465를 사용하세요.")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/crawl")
def crawl_api(payload: CrawlRequest) -> dict[str, Any]:
    try:
        items = crawl_notice_titles_and_dates(payload.url, payload.limit)
        return {
            "ok": True,
            "count": len(items),
            "items": [{"title": title, "date": date} for title, date in items],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"크롤링 실패: {e}") from e


@app.post("/api/parse")
def parse_api(payload: ParseRequest) -> dict[str, Any]:
    result: dict[str, Any] = {
        "ok": True,
        "hwp": {"ok": False, "error": ""},
        "pdf": {"ok": False, "error": ""},
    }

    try:
        hwp_text = extract_hwp_text_with_hwp5txt(Path(payload.hwpPath))
        result["hwp"] = {
            "ok": True,
            "length": len(hwp_text),
            "readable": is_text_readable(hwp_text),
            "preview": _preview(hwp_text),
        }
    except Exception as e:
        result["hwp"] = {"ok": False, "error": str(e)}

    try:
        pdf_text = extract_pdf_text(Path(payload.pdfPath))
        result["pdf"] = {
            "ok": True,
            "length": len(pdf_text),
            "readable": is_text_readable(pdf_text),
            "preview": _preview(pdf_text),
        }
    except Exception as e:
        result["pdf"] = {"ok": False, "error": str(e)}

    result["ok"] = bool(result["hwp"]["ok"] or result["pdf"]["ok"])
    return result


@app.post("/api/smtp-test")
def smtp_test_api(payload: SmtpRequest) -> dict[str, Any]:
    try:
        _send_mail(payload)
        return {"ok": True, "message": "테스트 메일 전송 성공"}
    except (ValueError, smtplib.SMTPException) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SMTP 처리 중 예기치 못한 오류: {e}") from e
