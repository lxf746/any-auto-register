from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import tempfile
import threading
import unittest

from playwright.sync_api import sync_playwright

from core.browser_utils import build_proxy_config, dump_page_debug
from core.executors.playwright import PlaywrightExecutor


class _BrowserTestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/cookie-check"):
            body = (self.headers.get("Cookie") or "").encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)
            return

        body = """
<!doctype html>
<html lang="en">
  <body>
    <input id="name" />
    <button id="save" type="button" onclick="
      document.cookie = 'session=abc123; path=/';
      document.querySelector('#result').textContent = document.querySelector('#name').value;
    ">Save</button>
    <div id="result"></div>
  </body>
</html>
""".strip().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(length).decode("utf-8")
        body = json.dumps(
            {
                "raw": raw,
                "content_type": self.headers.get("Content-Type", ""),
            },
            ensure_ascii=False,
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Set-Cookie", "posted=yes; Path=/")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


class HeadlessBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _BrowserTestHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def test_build_proxy_config_supports_credentials(self):
        config = build_proxy_config("http://user:pass@127.0.0.1:8080")
        self.assertEqual(
            config,
            {
                "server": "http://127.0.0.1:8080",
                "username": "user",
                "password": "pass",
            },
        )

    def test_dump_page_debug_writes_to_cross_platform_temp_dir(self):
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_content("<html><body><h1>调试页</h1></body></html>")

            paths = dump_page_debug(page, "headless-browser-test")

            browser.close()

        screenshot_path = Path(paths["screenshot"])
        html_path = Path(paths["html"])
        self.assertTrue(screenshot_path.is_file())
        self.assertTrue(html_path.is_file())
        self.assertIn("any-auto-register", html_path.parts)
        self.assertEqual(str(html_path.parent.parent), tempfile.gettempdir())
        self.assertIn("调试页", html_path.read_text(encoding="utf-8"))

    def test_playwright_executor_can_drive_local_page_headlessly(self):
        with PlaywrightExecutor(headless=True) as executor:
            response = executor.get(self.base_url)
            self.assertEqual(response.status_code, 200)
            self.assertIn('id="name"', response.text)

            executor.fill("#name", "headless-user")
            executor.click("#save")
            self.assertEqual(
                executor.evaluate("() => document.querySelector('#result').textContent"),
                "headless-user",
            )
            self.assertEqual(executor.get_cookies().get("session"), "abc123")

            executor.set_cookies({"pref": "dark"}, domain="127.0.0.1")
            cookie_response = executor.get(f"{self.base_url}/cookie-check")
            self.assertIn("pref=dark", cookie_response.text)

            post_response = executor.post(f"{self.base_url}/submit", json={"hello": "world"})
            self.assertEqual(post_response.status_code, 200)
            self.assertEqual(post_response.json()["content_type"], "application/json")
            self.assertIn('"hello": "world"', post_response.json()["raw"])
            self.assertEqual(post_response.cookies.get("posted"), "yes")


if __name__ == "__main__":
    unittest.main(verbosity=2)
