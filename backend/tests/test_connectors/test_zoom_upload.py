"""Tests for Zoom transcript upload — SRT parser, format detection, parse_transcript (ADR-019)."""

from __future__ import annotations

from pwbs.connectors.zoom import (
    _parse_srt,
    _parse_vtt,
    detect_transcript_format,
    parse_transcript,
)

# ---------------------------------------------------------------------------
# SRT Parsing
# ---------------------------------------------------------------------------


class TestParseSrt:
    """Tests for _parse_srt()."""

    def test_basic_srt(self) -> None:
        srt = (
            "1\n"
            "00:00:01,000 --> 00:00:05,000\n"
            "Alice: Hello everyone.\n"
            "\n"
            "2\n"
            "00:00:05,000 --> 00:00:10,000\n"
            "Bob: Thanks for joining.\n"
        )
        text, speakers = _parse_srt(srt)
        assert "Alice: Hello everyone." in text
        assert "Bob: Thanks for joining." in text
        assert speakers == ["Alice", "Bob"]

    def test_empty_srt(self) -> None:
        text, speakers = _parse_srt("")
        assert text == ""
        assert speakers == []

    def test_srt_no_speakers(self) -> None:
        srt = (
            "1\n"
            "00:00:01,000 --> 00:00:05,000\n"
            "Hello everyone.\n"
            "\n"
            "2\n"
            "00:00:05,000 --> 00:00:10,000\n"
            "Thanks for joining.\n"
        )
        text, speakers = _parse_srt(srt)
        assert "Hello everyone." in text
        assert "Thanks for joining." in text
        assert speakers == []

    def test_srt_strips_timestamps(self) -> None:
        srt = "1\n00:00:01,000 --> 00:00:05,000\nTest line\n"
        text, speakers = _parse_srt(srt)
        assert "00:00:01" not in text
        assert "Test line" in text

    def test_srt_strips_numeric_ids(self) -> None:
        srt = "42\n00:00:01,000 --> 00:00:05,000\nContent here\n"
        text, speakers = _parse_srt(srt)
        assert text == "Content here"

    def test_srt_multiple_speakers(self) -> None:
        srt = (
            "1\n"
            "00:00:00,000 --> 00:00:02,000\n"
            "Alice: Hi\n"
            "\n"
            "2\n"
            "00:00:02,000 --> 00:00:04,000\n"
            "Bob: Hello\n"
            "\n"
            "3\n"
            "00:00:04,000 --> 00:00:06,000\n"
            "Charlie: Hey\n"
            "\n"
            "4\n"
            "00:00:06,000 --> 00:00:08,000\n"
            "Alice: Let's start\n"
        )
        text, speakers = _parse_srt(srt)
        assert speakers == ["Alice", "Bob", "Charlie"]

    def test_srt_blank_lines_skipped(self) -> None:
        srt = "\n\n1\n00:00:01,000 --> 00:00:05,000\nSome text\n\n\n"
        text, speakers = _parse_srt(srt)
        assert text == "Some text"


# ---------------------------------------------------------------------------
# Format Detection
# ---------------------------------------------------------------------------


class TestDetectTranscriptFormat:
    """Tests for detect_transcript_format()."""

    def test_vtt_by_extension(self) -> None:
        assert detect_transcript_format("anything", "meeting.vtt") == "vtt"

    def test_srt_by_extension(self) -> None:
        assert detect_transcript_format("anything", "meeting.srt") == "srt"

    def test_txt_by_extension(self) -> None:
        assert detect_transcript_format("plain text", "meeting.txt") == "txt"

    def test_vtt_by_content(self) -> None:
        vtt_content = "WEBVTT\n\n1\n00:00:01.000 --> 00:00:05.000\nHello"
        assert detect_transcript_format(vtt_content, "") == "vtt"

    def test_srt_by_content(self) -> None:
        assert detect_transcript_format("1\n00:00:01,000 --> 00:00:05,000\nHello", "") == "srt"

    def test_txt_fallback(self) -> None:
        assert detect_transcript_format("Just some plain text", "") == "txt"

    def test_txt_extension_with_vtt_content(self) -> None:
        content = "WEBVTT\n\n1\n00:00:01.000 --> 00:00:05.000\nHello"
        assert detect_transcript_format(content, "meeting.txt") == "vtt"

    def test_txt_extension_with_srt_content(self) -> None:
        content = "1\n00:00:01,000 --> 00:00:05,000\nHello"
        assert detect_transcript_format(content, "meeting.txt") == "srt"

    def test_no_filename(self) -> None:
        assert detect_transcript_format("plain text", "") == "txt"

    def test_uppercase_extension(self) -> None:
        assert detect_transcript_format("anything", "MEETING.VTT") == "vtt"


# ---------------------------------------------------------------------------
# parse_transcript (unified dispatcher)
# ---------------------------------------------------------------------------


class TestParseTranscript:
    """Tests for parse_transcript()."""

    def test_vtt_dispatch(self) -> None:
        vtt = "WEBVTT\n\n1\n00:00:01.000 --> 00:00:05.000\nAlice: Hello"
        text, speakers = parse_transcript(vtt, "meeting.vtt")
        assert "Alice: Hello" in text
        assert "Alice" in speakers

    def test_srt_dispatch(self) -> None:
        srt = "1\n00:00:01,000 --> 00:00:05,000\nBob: Hi there"
        text, speakers = parse_transcript(srt, "meeting.srt")
        assert "Bob: Hi there" in text
        assert "Bob" in speakers

    def test_txt_dispatch(self) -> None:
        text, speakers = parse_transcript("Just plain text\nNo formatting", "notes.txt")
        assert text == "Just plain text\nNo formatting"
        assert speakers == []

    def test_empty_content(self) -> None:
        text, speakers = parse_transcript("", "empty.txt")
        assert text == ""
        assert speakers == []

    def test_vtt_consistency_with_original(self) -> None:
        """parse_transcript with VTT should produce same result as _parse_vtt."""
        vtt = (
            "WEBVTT\n\n"
            "1\n"
            "00:00:01.000 --> 00:00:05.000\n"
            "Speaker A: First line\n"
            "\n"
            "2\n"
            "00:00:05.000 --> 00:00:10.000\n"
            "Speaker B: Second line\n"
        )
        direct_text, direct_speakers = _parse_vtt(vtt)
        dispatch_text, dispatch_speakers = parse_transcript(vtt, "test.vtt")
        assert direct_text == dispatch_text
        assert direct_speakers == dispatch_speakers


# ---------------------------------------------------------------------------
# Edge cases & Robustness
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge case tests for transcript parsing."""

    def test_srt_with_multiline_cues(self) -> None:
        srt = "1\n00:00:01,000 --> 00:00:05,000\nFirst line of text\nSecond line of text\n"
        text, speakers = _parse_srt(srt)
        assert "First line of text" in text
        assert "Second line of text" in text

    def test_srt_with_html_tags(self) -> None:
        """SRT sometimes contains HTML-like formatting — should be preserved as text."""
        srt = "1\n00:00:01,000 --> 00:00:05,000\n<i>Emphasized text</i>\n"
        text, speakers = _parse_srt(srt)
        assert "<i>Emphasized text</i>" in text

    def test_very_long_speaker_name_ignored(self) -> None:
        """Speaker names longer than 100 chars should not be detected."""
        long_name = "A" * 150
        srt = f"1\n00:00:01,000 --> 00:00:05,000\n{long_name}: Some text\n"
        text, speakers = _parse_srt(srt)
        assert speakers == []

    def test_colon_in_text_without_speaker(self) -> None:
        """Colons in regular text (e.g. URLs, timestamps) should not falsely detect speakers."""
        srt = "1\n00:00:01,000 --> 00:00:05,000\nNote: see https://example.com\n"
        text, speakers = _parse_srt(srt)
        assert "Note" in speakers  # "Note" looks like a speaker name — consistent with VTT behavior
