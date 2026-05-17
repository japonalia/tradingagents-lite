from __future__ import annotations

import os
from typing import Any

import pandas as pd
import requests
from dotenv import load_dotenv

from src.data_sources.base import MarketDataResult

DEFAULT_TVREMIX_MCP_URL = "https://tvremix.xyz/api/mcp/v1"
MISSING_CONFIG_MESSAGE = (
    "TVRemix MCP no está configurado. Define TVREMIX_MCP_URL y TVREMIX_API_KEY."
)
PARTIAL_SCHEMA_WARNING = "TVRemix conectado parcialmente / schema pendiente de mapear"


load_dotenv()


def _get_tvremix_config() -> tuple[str | None, str | None]:
    raw_url = os.getenv("TVREMIX_MCP_URL", "").strip()
    raw_key = os.getenv("TVREMIX_API_KEY", "").strip()

    url = raw_url or DEFAULT_TVREMIX_MCP_URL
    api_key = raw_key or None
    return url, api_key


def _build_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def list_tools(timeout: float = 10.0) -> dict[str, Any] | None:
    url, api_key = _get_tvremix_config()
    if not url or not api_key:
        raise ValueError(MISSING_CONFIG_MESSAGE)

    endpoint = f"{url.rstrip('/')}/tools/list"

    try:
        response = requests.get(endpoint, headers=_build_headers(api_key), timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"TVRemix MCP tools/list falló: {exc}") from exc
    except ValueError as exc:
        raise RuntimeError(f"TVRemix MCP tools/list devolvió JSON inválido: {exc}") from exc


def call_tool(tool_name: str, arguments: dict[str, Any], timeout: float = 20.0) -> dict[str, Any] | None:
    url, api_key = _get_tvremix_config()
    if not url or not api_key:
        raise ValueError(MISSING_CONFIG_MESSAGE)

    endpoint = f"{url.rstrip('/')}/tools/call"
    payload = {
        "name": tool_name,
        "arguments": arguments,
    }

    try:
        response = requests.post(
            endpoint,
            headers=_build_headers(api_key),
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"TVRemix MCP tools/call falló: {exc}") from exc
    except ValueError as exc:
        raise RuntimeError(f"TVRemix MCP tools/call devolvió JSON inválido: {exc}") from exc


def fetch_tvremix_data(symbol: str) -> MarketDataResult:
    normalized_symbol = symbol.upper().strip()
    if not normalized_symbol:
        raise ValueError("El ticker no puede estar vacío.")

    url, api_key = _get_tvremix_config()
    if not url or not api_key:
        raise ValueError(MISSING_CONFIG_MESSAGE)

    warnings: list[str] = []
    tools_payload: dict[str, Any] | None = None
    call_payload: dict[str, Any] | None = None

    try:
        tools_payload = list_tools()
    except Exception as exc:
        warnings.append(f"Aviso TVRemix: no se pudo consultar tools/list: {exc}")

    if tools_payload is not None:
        try:
            call_payload = call_tool("get_ticker_data", {"symbol": normalized_symbol})
        except Exception as exc:
            warnings.append(f"Aviso TVRemix: no se pudo ejecutar tools/call: {exc}")

    if call_payload is None:
        raise RuntimeError(
            "TVRemix MCP no devolvió datos utilizables todavía; se aplicará fallback a yfinance."
        )

    warnings.append(PARTIAL_SCHEMA_WARNING)

    return MarketDataResult(
        symbol=normalized_symbol,
        source="tvremix",
        market_data={},
        history=pd.DataFrame(),
        missing_fields=[],
        warnings=warnings,
    )
