import os
import pytest
from src.config import Config
from src.ai import _split_llm_name, _get_missing_llm_key_error, _build_transcript_model, SUPPORTED_LLM_PROVIDERS


def test_gemini_provider_supported():
    assert "gemini" in SUPPORTED_LLM_PROVIDERS
    assert "google" in SUPPORTED_LLM_PROVIDERS
    assert "google-gla" in SUPPORTED_LLM_PROVIDERS


def test_split_gemini_llm_name():
    assert _split_llm_name("gemini:gemini-3-flash-preview") == ("gemini", "gemini-3-flash-preview")
    assert _split_llm_name("gemini-3-flash-preview") == ("gemini", "gemini-3-flash-preview")
    assert _split_llm_name("google:gemini-3-flash-preview") == ("google", "gemini-3-flash-preview")
    assert _split_llm_name("google-gla:gemini-3-flash-preview") == ("google-gla", "gemini-3-flash-preview")


def test_gemini_model_builder(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test_key_gemini")
    config = Config()
    assert config.gemini_api_key == "test_key_gemini"
    assert config.google_api_key == "test_key_gemini"

    model_target = _build_transcript_model(config, "gemini:gemini-3-flash-preview")
    assert model_target == "google:gemini-3-flash-preview"

    error = _get_missing_llm_key_error("gemini:gemini-3-flash-preview", config)
    assert error is None


def test_gemini_missing_key_error(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    config = Config()
    error = _get_missing_llm_key_error("gemini:gemini-3-flash-preview", config)
    assert error is not None
    assert "GEMINI_API_KEY or GOOGLE_API_KEY is not set" in error
