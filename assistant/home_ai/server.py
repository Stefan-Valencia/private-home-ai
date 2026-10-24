from __future__ import annotations

import asyncio
from collections.abc import Sequence
import json
import mimetypes
import socket
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)

from .agent import (
    AssistantDeps,
    AssistantUserError,
    ModelUnavailable,
    ToolPolicy,
    build_assistant,
    build_local_http_client,
    build_local_model,
    manager_usage_limits,
    sanitize_user_output,
)
from .config import ConfigurationError, Settings
from .documents import DocumentError, DocumentStore, MAX_UPLOAD_BYTES


WEB_DIR = Path(__file__).resolve().parent / "web"
MAX_PROMPT_CHARS = 8_000
MAX_HISTORY_MESSAGES = 10
MAX_CONTEXT_CHARS = 12_000
MAX_JSON_BYTES = 64 * 1024
RUN_TIMEOUT_SECONDS = 300
REQUEST_BODY_TIMEOUT_SECONDS = 10
REQUEST_BODY_CHUNK_BYTES = 64 * 1024


def build_chat_message_history(history: object, prompt: str) -> list[ModelMessage]:
    """Build bounded user/assistant text history; client tool messages are never accepted."""
    if not isinstance(history, list):
        raise ValueError("Conversation history must be an array of text messages.")
    if len(history) > MAX_HISTORY_MESSAGES:
        raise ValueError("This chat has reached its temporary context limit. Start a new chat to continue.")
    if len(history) % 2:
        raise ValueError("Conversation history must contain complete user/assistant turns.")

    prompt_chars = len(prompt.strip())
    if prompt_chars > MAX_PROMPT_CHARS:
        raise ValueError(f"Prompts are limited to {MAX_PROMPT_CHARS} characters.")
    total_chars = prompt_chars
    messages: list[ModelMessage] = []

    for index, item in enumerate(history):
        expected_role = "user" if index % 2 == 0 else "assistant"
        if not isinstance(item, dict) or set(item) != {"role", "content"}:
            raise ValueError("Conversation history accepts only user and assistant text messages.")
        role = item["role"]
        content = item["content"]
        if role != expected_role:
            raise ValueError("Conversation history must alternate user and assistant messages.")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Conversation messages must contain non-empty text.")
        if len(content) > MAX_PROMPT_CHARS:
            raise ValueError(f"Conversation messages are limited to {MAX_PROMPT_CHARS} characters.")
        total_chars += len(content)
        if total_chars > MAX_CONTEXT_CHARS:
            raise ValueError(
                f"Conversation text is limited to {MAX_CONTEXT_CHARS:,} characters. "
                "Start a new chat or shorten your question."
            )
        if role == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=content)]))
        else:
            messages.append(ModelResponse(parts=[TextPart(content=content)]))

    return messages


def _usage_limit_message(error: UsageLimitExceeded) -> str:
    details = str(error).casefold()
    if "input_tokens_limit" in details or "total_tokens_limit" in details:
        return "This conversation reached the local model's context limit. Start a new chat or shorten your question."
    return "The local model's usage limit was reached. Start a new chat or try again with a shorter request."


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args: object, **_kwargs: object) -> None:
        return None


def build_local_url_opener() -> urllib.request.OpenerDirector:
    # Local health checks must bypass environment proxies and never follow a redirect.
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirectHandler())


class HomeAIService:
    def __init__(
        self,
        settings: Settings,
        *,
        model: object | None = None,
        documents: DocumentStore | None = None,
        run_timeout_seconds: int = RUN_TIMEOUT_SECONDS,
    ) -> None:
        if run_timeout_seconds < 1:
            raise ValueError("The inference timeout must be a positive integer.")
        self.settings = settings
        if model is None:
            self._local_http_client = build_local_http_client()
            model = build_local_model(settings, http_client=self._local_http_client)
        else:
            self._local_http_client = None
        self.documents = documents if documents is not None else DocumentStore(settings.data_dir / "documents.sqlite3")
        self.run_timeout_seconds = run_timeout_seconds
        self.policy = ToolPolicy()
        self.is_fake_model = self._local_http_client is None
        self.agent = build_assistant(settings, model=model)
        self._inference_slot = threading.BoundedSemaphore(1)
        self._url_opener = build_local_url_opener()
        self._inference_loop = asyncio.new_event_loop()
        self._inference_thread = threading.Thread(
            target=self._inference_loop.run_forever,
            name="private-home-ai-inference",
            daemon=True,
        )
        self._inference_thread.start()
        self._closed = False

    def close(self) -> None:
        if self._closed:
            return
        try:
            if self._local_http_client is not None:
                closing = asyncio.run_coroutine_threadsafe(
                    self._local_http_client.aclose(), self._inference_loop
                )
                closing.result(timeout=5)
                self._local_http_client = None
        finally:
            self._inference_loop.call_soon_threadsafe(self._inference_loop.stop)
            self._inference_thread.join(timeout=5)
            self._inference_loop.close()
            self.documents.close()
            self._closed = True

    async def _run_agent(
        self,
        prompt: str,
        deps: AssistantDeps,
        message_history: Sequence[ModelMessage],
    ) -> str:
        try:
            result = await self.agent.run(
                prompt,
                deps=deps,
                message_history=message_history,
                usage_limits=manager_usage_limits(),
                timeout=self.run_timeout_seconds,
            )
        except UsageLimitExceeded as exc:
            raise AssistantUserError(_usage_limit_message(exc)) from exc
        return sanitize_user_output(result.output)

    def inference_ready(self) -> bool:
        url = self.settings.inference_endpoint + "/models"
        request = urllib.request.Request(url, method="GET", headers={"Accept": "application/json"})
        try:
            with self._url_opener.open(request, timeout=1.5) as response:
                return response.status == 200
        except (OSError, urllib.error.URLError, TimeoutError):
            return False

    def _chat_with_deps(
        self,
        prompt: str,
        *,
        message_history: Sequence[ModelMessage] = (),
    ) -> tuple[str, AssistantDeps]:
        prompt = prompt.strip()
        if not prompt:
            raise ValueError("Enter a question first.")
        if len(prompt) > MAX_PROMPT_CHARS:
            raise ValueError(f"Prompts are limited to {MAX_PROMPT_CHARS} characters.")
        if not self.is_fake_model and not self.inference_ready():
            raise ModelUnavailable("The local model is not running. Start it on this computer and try again.")
        if not self._inference_slot.acquire(blocking=False):
            raise AssistantUserError("The local model is busy. Wait for the current answer to finish.")
        deps = AssistantDeps(self.documents, self.policy)
        try:
            running = asyncio.run_coroutine_threadsafe(
                self._run_agent(prompt, deps, message_history), self._inference_loop
            )
            try:
                return running.result(timeout=self.run_timeout_seconds + 1), deps
            except TimeoutError as exc:
                running.cancel()
                raise AssistantUserError("The local assistant took too long to respond. Try again.") from exc
        finally:
            self._inference_slot.release()

    def chat(
        self, prompt: str, *, message_history: Sequence[ModelMessage] = ()
    ) -> str:
        answer, _deps = self._chat_with_deps(prompt, message_history=message_history)
        return answer

    def chat_with_trace(
        self, prompt: str, *, message_history: Sequence[ModelMessage] = ()
    ) -> tuple[str, AssistantDeps]:
        """Return an ephemeral tool trace for local evaluation; nothing is persisted."""
        return self._chat_with_deps(prompt, message_history=message_history)


class LocalHTTPServer(ThreadingHTTPServer):
    daemon_threads = False
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], service: HomeAIService) -> None:
        self.service = service
        self.address_family = socket.AF_INET6 if ":" in address[0] else socket.AF_INET
        super().__init__(address, HomeAIRequestHandler)
        host = str(self.server_address[0])
        authority_host = f"[{host}]" if ":" in host else host
        self.authority = f"{authority_host}:{self.server_address[1]}"
        self.origin = f"http://{self.authority}"


class HomeAIRequestHandler(BaseHTTPRequestHandler):
    server: LocalHTTPServer

    def setup(self) -> None:
        super().setup()
        self.connection.settimeout(10)

    def log_message(self, _format: str, *_args: object) -> None:
        # Do not log prompts, filenames, or document contents.
        return

    def _send(self, status: int, payload: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(payload)

    def _json(self, status: int, value: object) -> None:
        payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self._send(status, payload, "application/json; charset=utf-8")

    def _same_local_origin(self) -> bool:
        host = self.headers.get("Host", "").strip().lower()
        if host != self.server.authority.lower():
            self._json(421, {"error": "Use the local assistant address shown at startup."})
            return False
        origin = self.headers.get("Origin")
        if origin is not None and origin.rstrip("/").lower() != self.server.origin.lower():
            self._json(403, {"error": "Cross-origin requests are not allowed."})
            return False
        return True

    def _require_content_type(self, expected: str) -> bool:
        actual = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if actual != expected:
            self._json(415, {"error": f"Content-Type must be {expected}."})
            return False
        return True

    def _body(self, limit: int) -> bytes:
        raw_length = self.headers.get("Content-Length", "")
        try:
            length = int(raw_length)
        except ValueError as exc:
            self.close_connection = True
            raise ValueError("A valid Content-Length header is required.") from exc
        if length < 0 or length > limit:
            self.close_connection = True
            raise OverflowError("The request body exceeds the size limit.")
        deadline = time.monotonic() + REQUEST_BODY_TIMEOUT_SECONDS
        chunks: list[bytes] = []
        remaining = length
        try:
            while remaining:
                time_left = deadline - time.monotonic()
                if time_left <= 0:
                    raise TimeoutError
                self.connection.settimeout(time_left)
                chunk = self.rfile.read(min(remaining, REQUEST_BODY_CHUNK_BYTES))
                if not chunk:
                    raise ValueError("The request body was incomplete.")
                chunks.append(chunk)
                remaining -= len(chunk)
        except (OSError, TimeoutError, ValueError) as exc:
            self.close_connection = True
            raise ValueError("The request body was incomplete or timed out.") from exc
        self.connection.settimeout(10)
        return b"".join(chunks)

    def do_GET(self) -> None:
        if not self._same_local_origin():
            return
        request_path = urlsplit(self.path).path
        if request_path == "/api/health":
            ready = self.server.service.is_fake_model or self.server.service.inference_ready()
            self._json(200, {"status": "ready" if ready else "waiting", "inference": "local-only"})
            return
        if request_path == "/api/documents":
            documents = self.server.service.documents.list_documents()
            self._json(
                200,
                {"documents": [
                    {
                        "document_id": doc.document_id,
                        "filename": doc.filename,
                        "pages": doc.pages,
                        "passages": doc.passages,
                    }
                    for doc in documents
                ]},
            )
            return
        files = {
            "/": "index.html",
            "/index.html": "index.html",
            "/app.js": "app.js",
            "/styles.css": "styles.css",
        }
        relative = files.get(self.path)
        if relative is None:
            self._json(404, {"error": "Not found."})
            return
        payload = (WEB_DIR / relative).read_bytes()
        content_type = mimetypes.guess_type(relative)[0] or "application/octet-stream"
        self._send(200, payload, content_type + ("; charset=utf-8" if content_type.startswith("text/") or "javascript" in content_type else ""))

    def do_POST(self) -> None:
        if not self._same_local_origin():
            return
        request_path = urlsplit(self.path).path
        if request_path == "/api/chat":
            if not self._require_content_type("application/json"):
                return
            try:
                body = self._body(MAX_JSON_BYTES)
                request = json.loads(body)
                if not isinstance(request, dict) or not isinstance(request.get("prompt"), str):
                    raise ValueError("Send a JSON object with a prompt string.")
                if set(request) - {"prompt", "history"}:
                    raise ValueError("Chat requests may include only a prompt and plain-text history.")
                message_history = build_chat_message_history(
                    request.get("history", []),
                    request["prompt"],
                )
                answer = self.server.service.chat(
                    request["prompt"],
                    message_history=message_history,
                )
                self._json(200, {"answer": answer})
            except OverflowError as exc:
                self._json(413, {"error": str(exc)})
            except AssistantUserError as exc:
                self._json(503, {"error": str(exc)})
            except json.JSONDecodeError:
                self._json(400, {"error": "The request was not valid JSON."})
            except ValueError as exc:
                self._json(400, {"error": str(exc)})
            except Exception:
                self._json(500, {"error": "The local assistant could not complete that request."})
            return
        if request_path == "/api/documents":
            if not self._require_content_type("application/octet-stream"):
                return
            try:
                body = self._body(MAX_UPLOAD_BYTES)
                filename = unquote(self.headers.get("X-Filename", ""))
                summary = self.server.service.documents.add_file(filename, body)
                self._json(
                    201,
                    {"filename": summary.filename, "pages": summary.pages, "passages": summary.passages},
                )
            except OverflowError as exc:
                self._json(413, {"error": str(exc)})
            except (ValueError, DocumentError) as exc:
                self._json(400, {"error": str(exc)})
            except Exception:
                self._json(500, {"error": "The document could not be added."})
            return
        self._json(404, {"error": "Not found."})

    def do_DELETE(self) -> None:
        if not self._same_local_origin():
            return
        request_path = urlsplit(self.path).path
        prefix = "/api/documents/"
        if not request_path.startswith(prefix):
            self._json(404, {"error": "Not found."})
            return
        document_id = request_path[len(prefix) :]
        if self.server.service.documents.delete(document_id):
            self._json(200, {"deleted": True})
        else:
            self._json(404, {"error": "Document not found."})


def main() -> None:
    try:
        settings = Settings.from_env()
    except ConfigurationError as exc:
        raise SystemExit(str(exc)) from exc
    service = HomeAIService(settings)
    server: LocalHTTPServer | None = None
    try:
        server = LocalHTTPServer((settings.bind_host, settings.port), service)
        print(f"Private Home AI local prototype: {server.origin}")
        print("Inference is loopback-only. The server has no cloud fallback and exposes no device controls.")
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if server is not None:
            server.server_close()
        service.close()


if __name__ == "__main__":
    main()
