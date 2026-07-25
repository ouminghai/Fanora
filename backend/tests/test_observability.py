from app.core import observability


def test_langfuse_missing_is_a_quiet_optional_dependency(monkeypatch) -> None:
    monkeypatch.setattr(observability.settings, "langfuse_enabled", True)
    monkeypatch.setattr(observability, "_callback_factory", None)
    monkeypatch.setattr(observability, "_callback_lookup_complete", False)

    def missing_module(_: str):
        raise ModuleNotFoundError("No module named 'langfuse.langchain'")

    monkeypatch.setattr(observability.importlib, "import_module", missing_module)
    exception_calls: list[tuple[object, ...]] = []
    warning_calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(observability.logger, "exception", lambda *args, **kwargs: exception_calls.append(args))
    monkeypatch.setattr(observability.logger, "warning", lambda *args, **kwargs: warning_calls.append(args))

    assert observability.get_llm_callbacks() == []
    assert observability.get_llm_callbacks() == []
    assert exception_calls == []
    assert len(warning_calls) == 1
