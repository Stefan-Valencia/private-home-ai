from __future__ import annotations

import ipaddress
import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit


class ConfigurationError(ValueError):
    """Raised when configuration would expose data to a non-local service."""


def default_data_dir() -> Path:
    if os.name == "nt":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return root / "private-home-ai"


def validate_local_endpoint(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme != "http" or parsed.username or parsed.password:
        raise ConfigurationError("Inference must use an unauthenticated local HTTP endpoint.")
    if parsed.query or parsed.fragment or not parsed.path.rstrip("/").endswith("/v1"):
        raise ConfigurationError("Inference endpoint must end with /v1 and have no query or fragment.")
    if not parsed.hostname:
        raise ConfigurationError("Inference endpoint must use a loopback IP address.")
    try:
        address = ipaddress.ip_address(parsed.hostname)
    except ValueError as exc:
        raise ConfigurationError("Inference endpoint must use a loopback IP address, not a hostname.") from exc
    if not address.is_loopback:
        raise ConfigurationError("Remote inference endpoints are disabled; use a loopback address.")
    try:
        parsed.port
    except ValueError as exc:
        raise ConfigurationError("Inference endpoint port is invalid.") from exc
    return value.rstrip("/")


@dataclass(frozen=True)
class Settings:
    inference_endpoint: str = "http://127.0.0.1:8080/v1"
    model_name: str = "local-model"
    bind_host: str = "127.0.0.1"
    port: int = 4174
    data_dir: Path = field(default_factory=default_data_dir)

    @classmethod
    def from_env(cls) -> Settings:
        endpoint = validate_local_endpoint(
            os.environ.get("HOME_AI_MODEL_ENDPOINT", "http://127.0.0.1:8080/v1")
        )
        bind_host = os.environ.get("HOME_AI_HOST", "127.0.0.1")
        try:
            if not ipaddress.ip_address(bind_host).is_loopback:
                raise ConfigurationError("The unauthenticated prototype may bind only to loopback.")
        except ValueError as exc:
            raise ConfigurationError("HOME_AI_HOST must be a loopback IP address.") from exc
        try:
            port = int(os.environ.get("HOME_AI_PORT", "4174"))
        except ValueError as exc:
            raise ConfigurationError("HOME_AI_PORT must be an integer.") from exc
        if not 1 <= port <= 65535:
            raise ConfigurationError("HOME_AI_PORT must be between 1 and 65535.")
        return cls(
            inference_endpoint=endpoint,
            model_name=os.environ.get("HOME_AI_MODEL_NAME", "local-model"),
            bind_host=bind_host,
            port=port,
            data_dir=Path(os.environ.get("HOME_AI_DATA_DIR", str(default_data_dir()))),
        )
