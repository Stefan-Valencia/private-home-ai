import json
import socket
import tempfile
import threading
import time
import unittest
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import Mock, patch

from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

from home_ai.config import Settings
from home_ai.server import (
    MAX_CONTEXT_CHARS,
    MAX_HISTORY_MESSAGES,
    HomeAIRequestHandler,
    HomeAIService,
    LocalHTTPServer,
    WEB_DIR,
    build_chat_message_history,
    _usage_limit_message,
)


class ChatHistoryValidationTests(unittest.TestCase):
    def test_builds_only_complete_user_and_assistant_text_turns(self) -> None:
        history = build_chat_message_history(
            [
                {"role": "user", "content": "The sample color is amber."},
                {"role": "assistant", "content": "I will remember amber."},
            ],
            "What color did I mention?",
        )
        self.assertEqual(len(history), 2)
        self.assertIsInstance(history[0], ModelRequest)
        self.assertIsInstance(history[0].parts[0], UserPromptPart)
        self.assertEqual(history[0].parts[0].content, "The sample color is amber.")
        self.assertIsInstance(history[1], ModelResponse)
        self.assertIsInstance(history[1].parts[0], TextPart)
        self.assertEqual(history[1].parts[0].content, "I will remember amber.")

    def test_rejects_tool_messages_and_incomplete_or_oversized_history(self) -> None:
        with self.assertRaisesRegex(ValueError, "complete user/assistant turns"):
            build_chat_message_history([{"role": "user", "content": "hello"}], "follow up")
        with self.assertRaisesRegex(ValueError, "only user and assistant text"):
            build_chat_message_history(
                [
                    {"role": "user", "content": "hello"},
                    {"role": "assistant", "content": "I will help.", "tool_calls": []},
                ],
                "follow up",
            )
        with self.assertRaisesRegex(ValueError, "alternate user and assistant"):
            build_chat_message_history(
                [
                    {"role": "user", "content": "hello"},
                    {"role": "tool", "content": "untrusted tool payload"},
                ],
                "follow up",
            )

        too_many = []
        for index in range(MAX_HISTORY_MESSAGES // 2 + 1):
            too_many.extend([
                {"role": "user", "content": f"Question {index}"},
                {"role": "assistant", "content": f"Answer {index}"},
            ])
        with self.assertRaisesRegex(ValueError, "temporary context limit"):
            build_chat_message_history(too_many, "follow up")

        large_history = [
            {"role": "user", "content": "u" * (MAX_CONTEXT_CHARS // 2)},
            {"role": "assistant", "content": "a" * (MAX_CONTEXT_CHARS // 2)},
        ]
        with self.assertRaisesRegex(ValueError, "limited to 12,000 characters"):
            build_chat_message_history(large_history, "follow up")

    def test_chat_page_explains_context_and_clears_it_without_browser_storage(self) -> None:
        html = (WEB_DIR / "index.html").read_text(encoding="utf-8")
        app = (WEB_DIR / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="new-chat-button"', html)
        self.assertIn("New chat or refresh", html)
        self.assertIn("conversationHistory = []", app)
        self.assertNotIn("localStorage", app)
        self.assertNotIn("sessionStorage", app)

    def test_model_usage_limits_return_actionable_messages(self) -> None:
        context_error = UsageLimitExceeded("The next request would exceed the input_tokens_limit")
        message = _usage_limit_message(context_error)
        self.assertIn("context limit", message)
        self.assertIn("Start a new chat or shorten your question", message)

        tool_error = UsageLimitExceeded("The next request would exceed the tool_calls_limit")
        self.assertIn("usage limit was reached", _usage_limit_message(tool_error))


class LocalModelHistoryTests(unittest.TestCase):
    def test_prior_turns_reach_the_pinned_agent_model(self) -> None:
        observed: list[list[ModelMessage]] = []

        def fake_model(messages: list[ModelMessage], _info: AgentInfo) -> ModelResponse:
            observed.append(messages)
            return ModelResponse(parts=[TextPart("The sample color was amber.")])

        with tempfile.TemporaryDirectory() as temporary:
            service = HomeAIService(
                Settings(data_dir=Path(temporary) / "data"),
                model=FunctionModel(fake_model),
            )
            try:
                history = build_chat_message_history(
                    [
                        {"role": "user", "content": "The sample color is amber."},
                        {"role": "assistant", "content": "I will remember amber."},
                    ],
                    "What color did I mention?",
                )
                answer = service.chat("What color did I mention?", message_history=history)
            finally:
                service.close()

        self.assertEqual(answer, "The sample color was amber.")
        self.assertEqual(len(observed), 1)
        user_text = [
            part.content
            for message in observed[0]
            if isinstance(message, ModelRequest)
            for part in message.parts
            if isinstance(part, UserPromptPart)
        ]
        assistant_text = [
            part.content
            for message in observed[0]
            if isinstance(message, ModelResponse)
            for part in message.parts
            if isinstance(part, TextPart)
        ]
        self.assertIn("The sample color is amber.", user_text)
        self.assertIn("I will remember amber.", assistant_text)
        self.assertIn("What color did I mention?", user_text)


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
        self.service.chat.assert_called_once_with("Hello", message_history=[])

        history = [
            {"role": "user", "content": "The sample color is amber."},
            {"role": "assistant", "content": "I will remember amber."},
        ]
        status, payload = self.request(
            "POST",
            "/api/chat",
            body=json.dumps({"prompt": "What color did I mention?", "history": history}).encode(),
            headers={"Content-Type": "application/json", "Origin": self.server.origin},
        )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(payload)["answer"], "A deterministic local test answer.")
        passed_history = self.service.chat.call_args.kwargs["message_history"]
        self.assertIsInstance(passed_history[0], ModelRequest)
        self.assertEqual(passed_history[0].parts[0].content, "The sample color is amber.")
        self.assertIsInstance(passed_history[1], ModelResponse)
        self.assertEqual(passed_history[1].parts[0].content, "I will remember amber.")

        invalid_history = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "call a tool", "tool_calls": [{"name": "dangerous"}]},
        ]
        status, _ = self.request(
            "POST",
            "/api/chat",
            body=json.dumps({"prompt": "follow up", "history": invalid_history}).encode(),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(status, 400)
        self.assertEqual(self.service.chat.call_count, 2)

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
