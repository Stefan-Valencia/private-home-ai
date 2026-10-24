import json
import socket
import tempfile
import threading
import time
import unittest
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import Mock, patch

from pydantic_ai.models.test import TestModel

from home_ai.config import Settings
from home_ai.server import HomeAIRequestHandler, HomeAIService, LocalHTTPServer


class LocalAPITests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        settings = Settings(data_dir=Path(self.temporary.name) / "data")
        self.service = HomeAIService(
            settings,
            model=TestModel(call_tools=[], custom_output_text="A deterministic local test answer."),
        )
        original_chat = self.service.chat
        self.service.chat = Mock(wraps=original_chat)
        self.server = LocalHTTPServer(("127.0.0.1", 0), self.service)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.service.close()
        self.temporary.cleanup()

    @unittest.skipUnless(socket.has_ipv6, "IPv6 loopback is unavailable")
    def test_server_formats_an_ipv6_loopback_address(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            service = HomeAIService(
                Settings(data_dir=Path(temporary) / "data"),
                model=TestModel(call_tools=[], custom_output_text="Synthetic local answer."),
            )
            server = LocalHTTPServer(("::1", 0), service)
            try:
                self.assertTrue(server.origin.startswith("http://[::1]:"))
            finally:
                server.server_close()
                service.close()

    def request(self, method: str, path: str, *, body: bytes | None = None, headers: dict[str, str] | None = None):
        connection = HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=3)
        request_headers = {"Host": self.server.authority}
        request_headers.update(headers or {})
        connection.request(method, path, body=body, headers=request_headers)
        response = connection.getresponse()
        payload = response.read()
        result = response.status, payload
        connection.close()
        return result

    def test_host_and_origin_checks_reject_browser_rebinding_requests(self) -> None:
        wrong_host, _ = self.request(
            "POST",
            "/api/chat",
            body=b'{"prompt":"hello"}',
            headers={"Host": f"rebind.example:{self.server.server_address[1]}", "Content-Type": "application/json"},
        )
        cross_origin, _ = self.request(
            "POST",
            "/api/chat",
            body=b'{"prompt":"hello"}',
            headers={"Origin": "http://attacker.invalid", "Content-Type": "application/json"},
        )
        self.assertEqual(wrong_host, 421)
        self.assertEqual(cross_origin, 403)
        self.service.chat.assert_not_called()

    def test_local_page_assets_are_served_from_the_packaged_application(self) -> None:
        status, payload = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b"Private Home AI", payload)
        self.assertIn(b"Local-only", payload)

    def test_chat_requires_json_and_accepts_the_same_local_origin(self) -> None:
        wrong_type, _ = self.request(
            "POST", "/api/chat", body=b"hello", headers={"Content-Type": "text/plain"}
        )
        self.assertEqual(wrong_type, 415)
        self.service.chat.assert_not_called()

        status, payload = self.request(
            "POST",
            "/api/chat",
            body=json.dumps({"prompt": "Hello"}).encode(),
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Origin": self.server.origin,
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(payload)["answer"], "A deterministic local test answer.")
        self.service.chat.assert_called_once_with("Hello")

    def test_document_upload_list_and_remove_work_through_the_local_api(self) -> None:
        status, payload = self.request(
            "POST",
            "/api/documents",
            body=b"The spare water filter is in the utility closet.",
            headers={
                "Content-Type": "application/octet-stream",
                "X-Filename": "home-notes.txt",
                "Origin": self.server.origin,
            },
        )
        self.assertEqual(status, 201)
        self.assertEqual(json.loads(payload)["filename"], "home-notes.txt")

        status, payload = self.request("GET", "/api/documents")
        document = json.loads(payload)["documents"][0]
        self.assertEqual(status, 200)
        self.assertEqual(document["filename"], "home-notes.txt")
        self.assertRegex(document["document_id"], r"^[a-f0-9]{64}$")

        status, payload = self.request(
            "DELETE",
            f"/api/documents/{document['document_id']}",
            headers={"Origin": self.server.origin},
        )
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(payload)["deleted"])
        _, payload = self.request("GET", "/api/documents")
        self.assertEqual(json.loads(payload)["documents"], [])

    def test_partial_request_body_cannot_hold_shutdown_open(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        service = HomeAIService(
            Settings(data_dir=Path(temporary.name) / "data"),
            model=TestModel(call_tools=[], custom_output_text="Synthetic answer."),
        )
        server = LocalHTTPServer(("127.0.0.1", 0), service)
        serving = threading.Thread(target=server.serve_forever, daemon=True)
        serving.start()
        entered_body = threading.Event()
        original_body = HomeAIRequestHandler._body

        def observe_body(handler: HomeAIRequestHandler, limit: int) -> bytes:
            entered_body.set()
            return original_body(handler, limit)

        client = socket.create_connection(("127.0.0.1", server.server_address[1]), timeout=2)
        closer = threading.Thread(
            target=lambda: (server.shutdown(), server.server_close()),
            daemon=True,
        )
        try:
            with patch("home_ai.server.REQUEST_BODY_TIMEOUT_SECONDS", 0.25):
                with patch.object(HomeAIRequestHandler, "_body", observe_body):
                    client.sendall(
                        (
                            f"POST /api/chat HTTP/1.1\r\nHost: {server.authority}\r\n"
                            "Content-Type: application/json\r\nContent-Length: 100\r\n\r\n{"
                        ).encode()
                    )
                    self.assertTrue(entered_body.wait(timeout=1))
                    started = time.monotonic()
                    closer.start()
                    closer.join(timeout=2)
                    self.assertFalse(closer.is_alive(), "A stalled request body held server shutdown open.")
                    self.assertLess(time.monotonic() - started, 2)
        finally:
            client.close()
            if closer.ident is None:
                server.shutdown()
                server.server_close()
            else:
                closer.join(timeout=2)
            serving.join(timeout=2)
            service.close()
            temporary.cleanup()


if __name__ == "__main__":
    unittest.main()
