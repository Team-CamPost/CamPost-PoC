# pip install pdfplumber
# HWP 파싱용:
# - Linux: sudo apt install -y hwp5xml
# - Windows: WSL(Ubuntu) 설치 후 WSL 내부에서 sudo apt install -y hwp5xml

from __future__ import annotations

import os
import subprocess
import shutil
from pathlib import Path

import pdfplumber


HWP_PATH = Path("test.hwp")
PDF_PATH = Path("봉사활동인증서_플로깅.pdf")


def to_wsl_path(path: Path) -> str:
    abs_path = path.resolve()
    path_str = str(abs_path).replace("\\", "/")

    if len(path_str) >= 2 and path_str[1] == ":":
        drive = path_str[0].lower()
        rest = path_str[2:]
        return f"/mnt/{drive}{rest}"

    return path_str


def run_hwp5txt_local(file_path: Path) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["hwp5txt", str(file_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def run_hwp5txt_wsl(file_path: Path) -> subprocess.CompletedProcess[bytes]:
    wsl_cmd = shutil.which("wsl") or shutil.which("wsl.exe")
    if wsl_cmd is None:
        raise RuntimeError(
            "Windows에서 HWP 파싱을 하려면 WSL이 필요합니다. "
            "PowerShell에서 'wsl --install -d Ubuntu'를 실행한 뒤 재시도하세요."
        )

    check_tool = subprocess.run(
        [
            wsl_cmd,
            "bash",
            "-lc",
            "command -v hwp5txt >/dev/null 2>&1 || test -x ~/.local/bin/hwp5txt",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check_tool.returncode != 0:
        raise RuntimeError(
            "WSL 내부에 hwp5txt가 없습니다. "
            "WSL(Ubuntu)에서 'sudo apt install -y pipx && pipx install pyhwp && pipx inject pyhwp six' 실행 후 재시도하세요."
        )

    # PATH에 없을 수 있어 ~/.local/bin 경로까지 포함해서 탐색
    hwp_cmd = "$(command -v hwp5txt || echo ~/.local/bin/hwp5txt)"
    return subprocess.run(
        [wsl_cmd, "bash", "-lc", f"{hwp_cmd} '{to_wsl_path(file_path)}'"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def extract_hwp_text_with_hwp5txt(file_path: Path) -> str:
    if not file_path.exists():
        raise FileNotFoundError(f"HWP 파일이 없습니다: {file_path}")

    # 1) 로컬 Linux/macOS에 hwp5txt가 있으면 직접 실행
    # 2) Windows면 WSL 내부 hwp5txt로 실행
    if shutil.which("hwp5txt") is not None:
        result = run_hwp5txt_local(file_path)
    elif os.name == "nt":
        result = run_hwp5txt_wsl(file_path)
    else:
        raise RuntimeError("hwp5txt 명령어를 찾을 수 없습니다. Linux 서버에 hwp5xml을 설치하세요.")

    if result.returncode != 0:
        stderr_text = result.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(f"hwp5txt 실행 실패: {stderr_text}")

    return result.stdout.decode("utf-8", errors="replace").strip()


def extract_pdf_text(file_path: Path) -> str:
    if not file_path.exists():
        raise FileNotFoundError(f"PDF 파일이 없습니다: {file_path}")

    pages_text = []
    with pdfplumber.open(str(file_path)) as pdf:
        for page in pdf.pages:
            pages_text.append(page.extract_text() or "")

    return "\n".join(pages_text).strip()


def is_text_readable(text: str, min_len: int = 20) -> bool:
    # 간단 검증: 길이 + 치환문자(깨짐 가능성) 비율 확인
    if len(text) < min_len:
        return False

    replacement_count = text.count("�")
    ratio = replacement_count / max(len(text), 1)
    return ratio < 0.05


def print_preview(name: str, text: str, preview_len: int = 200) -> None:
    print(f"\n[{name}] 길이: {len(text)}")
    print(f"[{name}] 가독성 체크: {'OK' if is_text_readable(text) else '주의'}")
    print(f"[{name}] 미리보기:\n{text[:preview_len]}\n")


def main() -> None:
    # HWP
    try:
        hwp_text = extract_hwp_text_with_hwp5txt(HWP_PATH)
        print_preview("HWP", hwp_text)
    except FileNotFoundError as e:
        print(e)
    except RuntimeError as e:
        print(e)
    except Exception as e:
        print(f"HWP 파싱 중 예외 발생: {e}")

    # PDF
    try:
        pdf_text = extract_pdf_text(PDF_PATH)
        print_preview("PDF", pdf_text)
    except FileNotFoundError as e:
        print(e)
    except Exception as e:
        print(f"PDF 파싱 중 예외 발생: {e}")


if __name__ == "__main__":
    main()
