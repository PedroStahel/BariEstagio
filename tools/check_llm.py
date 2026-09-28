"""Check LLM generation with a minimal prompt, without printing credentials."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parents[1]


def check(timeout: int = 30) -> int:
    config = dotenv_values(ROOT / ".env")
    key = config.get("LAUDOS_API_KEY")
    model = config.get("LAUDOS_MODEL")
    url = config.get("LAUDOS_API_URL")
    if not key or not model or not url:
        print("Configuração incompleta em .env: URL, modelo e chave são necessários.")
        return 1
    if not url.startswith("https://"):
        print("LAUDOS_API_URL precisa usar HTTPS.")
        return 1
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": "Responda apenas OK."}],
        "temperature": 0,
    }).encode("utf-8")
    request = Request(url, data=payload, headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    })
    started = time.monotonic()
    print(f"Testando geração mínima com {model} (limite {timeout}s)...", flush=True)
    try:
        with urlopen(request, timeout=timeout) as response:
            reply = json.load(response)
            content = reply["choices"][0]["message"]["content"]
            print(f"HTTP {response.status}; tempo: {time.monotonic()-started:.1f}s")
            print("Resposta:", str(content)[:100].replace("\n", " "))
            return 0
    except HTTPError as exc:
        detail = exc.read(600).decode("utf-8", errors="replace").replace(key, "[chave ocultada]")
        print(f"HTTP {exc.code}; tempo: {time.monotonic()-started:.1f}s; detalhe: {detail}")
    except (TimeoutError, URLError) as exc:
        print(f"Falha de conexão após {time.monotonic()-started:.1f}s: {type(exc).__name__}")
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"Resposta inesperada após {time.monotonic()-started:.1f}s: {type(exc).__name__}")
    return 1


if __name__ == "__main__":
    sys.exit(check())
