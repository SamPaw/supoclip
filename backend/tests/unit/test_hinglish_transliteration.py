"""Tests for Hindi Devanagari to Hinglish transliteration."""

import json
from pathlib import Path
from src.media.hinglish import (
    devanagari_to_hinglish,
    has_devanagari,
    transliterate_token,
    transliterate_transcript_words,
    transliterate_transcript_utterances,
    transliterate_transcript_payload,
)
from src.media.transcription import (
    _whisper_result_to_transcript_data,
    format_transcript_for_analysis,
    load_cached_transcript_data,
)
from src.media.captions import build_assemblyai_ass_subtitles


def test_has_devanagari():
    assert has_devanagari("ये क्या हो गया") is True
    assert has_devanagari("Hello world") is False
    assert has_devanagari("GTA 6 gameplay") is False
    assert has_devanagari("GTA 6 का गेमप्ले") is True
    assert has_devanagari("") is False
    assert has_devanagari(None) is False


def test_user_requested_example():
    """Verify the exact user example: 'ye kya hogaya' -> 'ye kya ho gaya'."""
    assert devanagari_to_hinglish("ये क्या हो गया") == "ye kya ho gaya"
    assert devanagari_to_hinglish("ये क्या hogaya") == "ye kya hogaya"
    assert devanagari_to_hinglish("ये क्या होगया") == "ye kya hogaya"


def test_common_conversational_phrases():
    assert devanagari_to_hinglish("नमस्ते दोस्तों") == "namaste dosto"
    assert devanagari_to_hinglish("कैसे हो आप सब?") == "kaise ho aap sab?"
    assert devanagari_to_hinglish("भाई चैनल को सब्सक्राइब करो।") == "bhai channel ko subscribe karo."
    assert devanagari_to_hinglish("ये वीडियो बहुत अच्छा है!") == "ye video bahut achha hai!"
    assert devanagari_to_hinglish("मुझे नहीं पता क्या हुआ था।") == "mujhe nahi pata kya hua tha."


def test_token_with_surrounding_punctuation_and_whitespace():
    assert transliterate_token(" क्या?") == " kya?"
    assert transliterate_token('"नमस्ते!"') == '"namaste!"'
    assert transliterate_token("  हो  ") == "  ho  "
    assert transliterate_token("English") == "English"
    assert transliterate_token("123") == "123"


def test_transliterate_transcript_words_preserves_timestamps():
    words = [
        {"text": " ये", "start": 100, "end": 350, "confidence": 0.95, "speaker": None},
        {"text": " क्या", "start": 350, "end": 600, "confidence": 0.92, "speaker": None},
        {"text": " हो", "start": 600, "end": 800, "confidence": 0.88, "speaker": None},
        {"text": " गया?", "start": 800, "end": 1200, "confidence": 0.99, "speaker": None},
        {"text": " bro!", "start": 1200, "end": 1500, "confidence": 0.97, "speaker": None},
    ]

    result = transliterate_transcript_words(words)
    assert len(result) == 5
    assert result[0]["text"] == " ye"
    assert result[0]["start"] == 100
    assert result[0]["end"] == 350
    assert result[1]["text"] == " kya"
    assert result[2]["text"] == " ho"
    assert result[3]["text"] == " gaya?"
    assert result[4]["text"] == " bro!"


def test_transliterate_transcript_payload():
    payload = {
        "version": 2,
        "text": "ये क्या हो गया? सब ठीक है।",
        "words": [
            {"text": "ये", "start": 0, "end": 200},
            {"text": "क्या", "start": 200, "end": 500},
            {"text": "हो", "start": 500, "end": 700},
            {"text": "गया?", "start": 700, "end": 1000},
        ],
        "utterances": [
            {
                "text": "ये क्या हो गया?",
                "start": 0,
                "end": 1000,
                "words": [
                    {"text": "ये", "start": 0, "end": 200},
                    {"text": "क्या", "start": 200, "end": 500},
                    {"text": "हो", "start": 500, "end": 700},
                    {"text": "गया?", "start": 700, "end": 1000},
                ],
            }
        ],
    }

    converted = transliterate_transcript_payload(payload)
    assert converted["text"] == "ye kya ho gaya? sab theek hai."
    assert converted["words"][0]["text"] == "ye"
    assert converted["words"][1]["text"] == "kya"
    assert converted["words"][2]["text"] == "ho"
    assert converted["words"][3]["text"] == "gaya?"
    assert converted["utterances"][0]["text"] == "ye kya ho gaya?"
    assert converted["utterances"][0]["words"][1]["text"] == "kya"


def test_whisper_result_to_transcript_data_translates_hindi():
    raw_whisper_result = {
        "text": "ये क्या हो गया",
        "language": "hi",
        "segments": [
            {
                "text": "ये क्या हो गया",
                "start": 0.0,
                "end": 1.2,
                "words": [
                    {"word": "ये", "start": 0.0, "end": 0.3, "probability": 0.9},
                    {"word": "क्या", "start": 0.3, "end": 0.6, "probability": 0.95},
                    {"word": "हो", "start": 0.6, "end": 0.8, "probability": 0.88},
                    {"word": "गया", "start": 0.8, "end": 1.2, "probability": 0.92},
                ],
            }
        ],
    }

    transcript_data = _whisper_result_to_transcript_data(raw_whisper_result)
    assert transcript_data["text"] == "ye kya ho gaya"
    assert transcript_data["words"][0]["text"] == "ye"
    assert transcript_data["words"][1]["text"] == "kya"
    assert transcript_data["words"][2]["text"] == "ho"
    assert transcript_data["words"][3]["text"] == "gaya"
    assert transcript_data["utterances"][0]["text"] == "ye kya ho gaya"


def test_format_transcript_for_analysis_with_hindi():
    raw_whisper_result = {
        "text": "ये क्या हो गया",
        "language": "hi",
        "segments": [
            {
                "text": "ये क्या हो गया",
                "start": 0.0,
                "end": 1.5,
            }
        ],
    }
    lines = format_transcript_for_analysis(raw_whisper_result)
    assert len(lines) == 1
    assert "ye kya ho gaya" in lines[0]
    assert "ये" not in lines[0]


def test_load_cached_transcript_data_converts_legacy_devanagari(tmp_path: Path):
    cache_file = tmp_path / "video.transcript_cache.json"
    legacy_payload = {
        "version": 2,
        "text": "नमस्ते दोस्तों",
        "words": [
            {"text": "नमस्ते", "start": 0, "end": 500},
            {"text": "दोस्तों", "start": 500, "end": 1000},
        ],
        "utterances": [
            {
                "text": "नमस्ते दोस्तों",
                "start": 0,
                "end": 1000,
                "words": [
                    {"text": "नमस्ते", "start": 0, "end": 500},
                    {"text": "दोस्तों", "start": 500, "end": 1000},
                ],
            }
        ],
    }
    cache_file.write_text(json.dumps(legacy_payload), encoding="utf-8")

    loaded = load_cached_transcript_data(tmp_path / "video.mp4")
    assert loaded is not None
    assert loaded["text"] == "namaste dosto"
    assert loaded["words"][0]["text"] == "namaste"
    assert loaded["words"][1]["text"] == "dosto"


def test_subtitles_render_in_english_script(tmp_path: Path, monkeypatch):
    from src.media import captions
    monkeypatch.setattr(captions, "emoji_rendering_supported", lambda: False)

    output_ass = tmp_path / "test_subs.ass"
    words = [
        {"text": "ये", "start": 0.0, "end": 0.4},
        {"text": "क्या", "start": 0.4, "end": 0.8},
        {"text": "हो", "start": 0.8, "end": 1.1},
        {"text": "गया", "start": 1.1, "end": 1.6},
    ]

    built = build_assemblyai_ass_subtitles(
        tmp_path / "dummy.mp4",
        0.0,
        2.0,
        1080,
        1920,
        output_ass,
        caption_words=words,
        hook_title="ये क्या हो गया",
    )
    assert built is True
    content = output_ass.read_text(encoding="utf-8")
    assert "YE" in content.upper() or "ye" in content.lower()
    assert "KYA" in content.upper() or "kya" in content.lower()
    assert "HO" in content.upper() or "ho" in content.lower()
    assert "GAYA" in content.upper() or "gaya" in content.lower()
    # Confirm no Devanagari characters exist in generated ASS subtitles
    assert not any("\u0900" <= c <= "\u097f" for c in content)
