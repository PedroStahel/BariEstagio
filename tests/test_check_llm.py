"""No-network check for the minimal API diagnostic."""

from tools import check_llm


def test_minimal_request_does_not_print_key(monkeypatch, capsys) -> None:
    monkeypatch.setattr(check_llm, "dotenv_values", lambda _: {
        "LAUDOS_API_URL": "https://example.invalid/chat/completions",
        "LAUDOS_MODEL": "test-model", "LAUDOS_API_KEY": "secret-marker",
    })
    class Response:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *args): return None
        def read(self, *args): return b'{"choices":[{"message":{"content":"OK"}}]}'
    def fake_open(request, timeout):
        assert timeout == 30
        assert request.get_header("Authorization") == "Bearer secret-marker"
        return Response()
    monkeypatch.setattr(check_llm, "urlopen", fake_open)
    assert check_llm.check() == 0
    output = capsys.readouterr().out
    assert "HTTP 200" in output and "Resposta: OK" in output
    assert "secret-marker" not in output
