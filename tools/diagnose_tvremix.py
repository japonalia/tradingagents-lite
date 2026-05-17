from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

DEFAULT_TVREMIX_MCP_URL = "https://tvremix.xyz/api/mcp/v1"
OUTPUT_PATH = Path("reports/generated/tvremix_tools_schema.json")
REQUEST_TIMEOUT_SECONDS = 15


def _redact_secrets(text: str, api_key: str) -> str:
    if not text:
        return text
    sanitized = text
    if api_key:
        sanitized = sanitized.replace(api_key, "***REDACTED_API_KEY***")
    return sanitized


def _safe_json_loads(raw_text: str) -> Any:
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        return {"raw_text": raw_text}


def _extract_tools(result_payload: Any) -> list[dict[str, Any]]:
    if isinstance(result_payload, list):
        return [tool for tool in result_payload if isinstance(tool, dict)]

    if isinstance(result_payload, dict):
        if isinstance(result_payload.get("tools"), list):
            return [tool for tool in result_payload["tools"] if isinstance(tool, dict)]
        if isinstance(result_payload.get("items"), list):
            return [tool for tool in result_payload["items"] if isinstance(tool, dict)]

    return []


def main() -> int:
    load_dotenv()

    tvremix_url = os.getenv("TVREMIX_MCP_URL", "").strip() or DEFAULT_TVREMIX_MCP_URL
    tvremix_api_key = os.getenv("TVREMIX_API_KEY", "").strip()

    missing_vars: list[str] = []
    if not os.getenv("TVREMIX_MCP_URL", "").strip():
        missing_vars.append("TVREMIX_MCP_URL")
    if not tvremix_api_key:
        missing_vars.append("TVREMIX_API_KEY")

    if missing_vars:
        print(
            "Error de configuración: faltan variables requeridas en .env -> "
            + ", ".join(missing_vars)
        )
        return 1

    headers = {
        "Authorization": f"Bearer {tvremix_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {},
    }

    try:
        response = requests.post(
            tvremix_url,
            headers=headers,
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        print(f"Error de red llamando TVRemix MCP: {exc}")
        return 1

    print(f"status_code: {response.status_code}")

    sanitized_body_text = _redact_secrets(response.text, tvremix_api_key)
    parsed_body = _safe_json_loads(sanitized_body_text)

    if not response.ok:
        print("tools/list falló. Body sanitizado:")
        print(json.dumps(parsed_body, ensure_ascii=False, indent=2))
        return 1

    result = parsed_body.get("result") if isinstance(parsed_body, dict) else None
    tools = _extract_tools(result)

    if not tools:
        print("No se encontraron tools en la respuesta (estructura no reconocida).")
    else:
        print(f"tools encontrados: {len(tools)}")
        for idx, tool in enumerate(tools, start=1):
            name = tool.get("name", "<sin nombre>")
            description = tool.get("description", "") or "<sin descripción>"
            input_schema = tool.get("inputSchema", "<no disponible>")

            print(f"\n[{idx}] {name}")
            print(f"  descripción: {description}")
            print("  inputSchema:")
            print(json.dumps(input_schema, ensure_ascii=False, indent=2))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    sanitized_report = {
        "status_code": response.status_code,
        "request": {
            "url": tvremix_url,
            "jsonrpc": "2.0",
            "id": payload["id"],
            "method": payload["method"],
            "params": payload["params"],
        },
        "response": parsed_body,
        "tools": tools,
    }
    OUTPUT_PATH.write_text(
        json.dumps(sanitized_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nSchema sanitizado guardado en: {OUTPUT_PATH}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
