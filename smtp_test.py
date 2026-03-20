# pip install (표준 라이브러리만 사용: 추가 설치 불필요)

from __future__ import annotations

import os
import smtplib
from pathlib import Path
from email.message import EmailMessage


def load_dotenv_file(env_path: Path = Path(".env")) -> None:
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


load_dotenv_file()


# ===== SMTP 설정 =====
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))  # 587(StartTLS) 또는 465(SSL)
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

# ===== 메일 정보 =====
FROM_EMAIL = SMTP_USER
TO_EMAIL = os.getenv("TO_EMAIL", "")
SUBJECT = "[PoC] SMTP 테스트 메일"
BODY = "학교 SMTP 서버를 통한 메일 발송 테스트입니다."

# 인증용 서비스 운영 시 학교 도메인만 허용하는 옵션
ALLOWED_DOMAIN = os.getenv("ALLOWED_DOMAIN", "dankook.ac.kr")
ALLOW_EXTERNAL_RECIPIENT = os.getenv("ALLOW_EXTERNAL_RECIPIENT", "false").lower() == "true"


def validate_config() -> None:
    missing = []
    if not SMTP_USER:
        missing.append("SMTP_USER")
    if not SMTP_PASSWORD:
        missing.append("SMTP_PASSWORD")
    if not TO_EMAIL:
        missing.append("TO_EMAIL")

    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"환경변수가 비어 있습니다: {joined}")


def validate_recipient_domain(recipient: str) -> None:
    if ALLOW_EXTERNAL_RECIPIENT:
        return
    if not recipient.lower().endswith(f"@{ALLOWED_DOMAIN}"):
        raise ValueError(
            f"수신자는 @{ALLOWED_DOMAIN} 도메인만 허용됩니다. "
            "외부 메일 테스트가 필요하면 ALLOW_EXTERNAL_RECIPIENT=true로 실행하세요."
        )


def build_message() -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = FROM_EMAIL
    msg["To"] = TO_EMAIL
    msg["Subject"] = SUBJECT
    msg.set_content(BODY)
    return msg


def send_test_mail() -> None:
    validate_config()
    validate_recipient_domain(TO_EMAIL)
    msg = build_message()

    if SMTP_PORT == 587:
        # StartTLS 방식
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=20) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
    elif SMTP_PORT == 465:
        # SSL/TLS 방식
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=20) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
    else:
        raise ValueError("SMTP_PORT는 587 또는 465를 사용하세요.")


def main() -> None:
    try:
        send_test_mail()
        print("테스트 메일 전송 성공")
    except ValueError as e:
        print(f"설정 오류: {e}")
    except smtplib.SMTPAuthenticationError:
        print("인증 실패: 아이디/비밀번호를 확인하세요.")
    except smtplib.SMTPConnectError:
        print("서버 연결 실패: SMTP 서버 주소/포트를 확인하세요.")
    except smtplib.SMTPException as e:
        print(f"SMTP 오류 발생: {e}")
    except Exception as e:
        print(f"예상치 못한 오류: {e}")


if __name__ == "__main__":
    main()
