"""
CamPost Demo Server
수집된 공지를 브라우저로 확인하는 데모용 로컬 서버

실행: python demo.py
"""

import json
import mimetypes
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, unquote

# 스크립트 위치 기준 절대경로 — 어느 디렉토리에서 실행해도 동작
BASE_DIR     = Path(__file__).resolve().parent
NOTICES_FILE = BASE_DIR / "data" / "collected_notices.json"
FILES_DIR    = BASE_DIR / "data" / "files"
PORT = 9090

CONTENT_TYPES = {
    ".pdf":  "application/pdf",
    ".hwp":  "application/x-hwp",
    ".hwpx": "application/x-hwpx",
    ".zip":  "application/zip",
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png":  "image/png",
}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path

        if path in ("/", "/index.html"):
            self._serve_html()
        elif path == "/api/notices":
            self._serve_json()
        elif path.startswith("/files/"):
            self._serve_file(path[len("/files/"):])
        else:
            self.send_error(404)

    def _serve_html(self):
        html = (BASE_DIR / "demo" / "index.html").read_text(encoding="utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def _serve_json(self):
        data = NOTICES_FILE.read_text(encoding="utf-8") if NOTICES_FILE.exists() else "[]"
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data.encode("utf-8"))

    def _serve_file(self, filename: str):
        filename = unquote(filename)
        # 경로 탈출 방지: 파일명만 허용
        safe_name = Path(filename).name
        file_path = FILES_DIR / safe_name

        if not file_path.exists():
            self.send_error(404)
            return

        ext = file_path.suffix.lower()
        content_type = CONTENT_TYPES.get(ext, "application/octet-stream")
        data = file_path.read_bytes()

        # 한글 파일명 RFC 5987 인코딩 (브라우저 파일명 깨짐 방지)
        encoded_name = urllib.parse.quote(safe_name)

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header(
            "Content-Disposition",
            f"attachment; filename*=UTF-8''{encoded_name}"
        )
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    url = f"http://localhost:{PORT}"
    print(f"CamPost 데모 서버 시작: {url}")
    print("종료: Ctrl+C\n")
    webbrowser.open(url)
    ThreadingHTTPServer(("", PORT), Handler).serve_forever()
