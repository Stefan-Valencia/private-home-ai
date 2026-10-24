import os
import urllib.request
import unittest
from unittest.mock import patch

from home_ai.agent import build_local_http_client
from home_ai.config import ConfigurationError, Settings, validate_local_endpoint
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


class SettingsConstructionTests(unittest.TestCase):
    def test_direct_settings_reject_remote_inference_endpoint(self) -> None:
        with self.assertRaises(ConfigurationError):
            Settings(inference_endpoint="http://192.0.2.10:8080/v1")

    def test_direct_settings_reject_non_loopback_bind_hosts(self) -> None:
        for host in ("0.0.0.0", "192.0.2.10", "localhost"):
            with self.subTest(host=host), self.assertRaises(ConfigurationError):
                Settings(bind_host=host)

    def test_direct_settings_reject_invalid_ports(self) -> None:
        for port in (0, 65536, True, "4174"):
            with self.subTest(port=port), self.assertRaises(ConfigurationError):
                Settings(port=port)

    def test_direct_settings_accept_and_normalize_loopback_endpoint(self) -> None:
        settings = Settings(inference_endpoint="http://127.0.0.1:8080/v1/")
        self.assertEqual(settings.inference_endpoint, "http://127.0.0.1:8080/v1")


if __name__ == "__main__":
    unittest.main()
