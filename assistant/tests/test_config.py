import os
import urllib.request
import unittest
from unittest.mock import patch

from home_ai.agent import build_local_http_client
from home_ai.config import ConfigurationError, validate_local_endpoint
from home_ai.server import NoRedirectHandler, build_local_url_opener


class EndpointTests(unittest.TestCase):
    def test_accepts_ipv4_loopback(self) -> None:
        self.assertEqual(
            validate_local_endpoint("http://127.0.0.1:8080/v1/"),
            "http://127.0.0.1:8080/v1",
        )

    def test_accepts_ipv6_loopback(self) -> None:
        self.assertEqual(validate_local_endpoint("http://[::1]:8080/v1"), "http://[::1]:8080/v1")

    def test_rejects_remote_and_hostname_endpoints(self) -> None:
        for endpoint in (
            "https://api.example.com/v1",
            "http://example.com/v1",
            "http://localhost:8080/v1",
            "http://127.0.0.1:8080/v1?proxy=remote",
            "http://user:password@127.0.0.1:8080/v1",
        ):
            with self.subTest(endpoint=endpoint), self.assertRaises(ConfigurationError):
                validate_local_endpoint(endpoint)

    def test_inference_client_ignores_proxy_environment(self) -> None:
        with patch.dict(
            os.environ,
            {
                "HTTP_PROXY": "http://proxy.invalid:8080",
                "HTTPS_PROXY": "http://proxy.invalid:8080",
                "ALL_PROXY": "http://proxy.invalid:8080",
            },
        ):
            client = build_local_http_client()
        self.assertFalse(client.trust_env)
        self.assertFalse(client.follow_redirects)

    def test_health_client_has_no_proxy_and_does_not_follow_redirects(self) -> None:
        with patch.dict(
            os.environ,
            {
                "HTTP_PROXY": "http://proxy.invalid:8080",
                "HTTPS_PROXY": "http://proxy.invalid:8080",
                "ALL_PROXY": "http://proxy.invalid:8080",
            },
        ):
            opener = build_local_url_opener()
        redirect = next(handler for handler in opener.handlers if isinstance(handler, NoRedirectHandler))
        self.assertFalse(any(isinstance(handler, urllib.request.ProxyHandler) for handler in opener.handlers))
        self.assertIsNone(
            redirect.redirect_request(
                urllib.request.Request("http://127.0.0.1:8080/v1/models"),
                None,
                302,
                "Found",
                {},
                "http://external.invalid/collect",
            )
        )


if __name__ == "__main__":
    unittest.main()
