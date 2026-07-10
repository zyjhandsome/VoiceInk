from __future__ import annotations

from unittest.mock import patch

import numpy as np

from tests.helpers.app_harness import app_harness
from voiceink.audio_utils import TARGET_SAMPLE_RATE


def _audio(seconds: float = 0.2) -> np.ndarray:
    return np.ones(int(TARGET_SAMPLE_RATE * seconds), dtype=np.float32)


def _start_continuous_user_session(app) -> None:
    with patch.object(app, "_start_continuous_listening") as start:
        app._on_continuous_hotkey_start()
        start.assert_called_once()


def _begin_and_finish_asr(app, paster, text: str, audio: np.ndarray | None = None):
    app._begin_transcription(audio if audio is not None else _audio())
    app._on_final_result(text)
    return paster.paste_async.call_args[0][1]


def _drive_segment(app, paster, text: str, result: str = "pasted") -> None:
    callback = _begin_and_finish_asr(app, paster, text)
    callback(result)


def _enqueued_records(history):
    return [call.args[0] for call in history.enqueue.call_args_list]


def test_start_enqueues_history_cleanup_once_with_active_session() -> None:
    with app_harness(
        {
            "history.retention_days": 7,
            "history.max_entries": 123,
        }
    ) as h:
        app = h["app"]
        app._current_session_id = "active-session"

        app.start()

        h["history"].enqueue_cleanup.assert_called_once_with(
            retention_days=7,
            max_entries=123,
            active_session_id="active-session",
        )


def test_quit_closes_history_before_saving_config() -> None:
    with app_harness() as h:
        events: list[str] = []
        h["history"].close.side_effect = lambda **_: events.append("history.close")
        h["config"].save_immediate.side_effect = lambda: events.append("config.save")

        h["app"]._quit()

        assert events[:2] == ["history.close", "config.save"]


def test_continuous_three_segments_share_session_and_increment_seq_with_texts() -> None:
    overrides = {
        "audio.trigger_mode": "continuous",
        "audio.input_source": "mixed",
        "llm.enabled": True,
        "llm.api_url": "https://api.example.test/v1",
        "llm.api_key": "key",
        "llm.model_name": "gpt-test",
        "stt.model_id": "fire-red-asr2-ctc-zh_en-int8",
    }
    with app_harness(overrides) as h:
        app = h["app"]
        app._current_session_id = "stale"
        app._current_seq = 42
        _start_continuous_user_session(app)

        for raw, polished in (
            ("raw one", "polished one"),
            ("raw two", "polished two"),
            ("raw three", "raw three"),
        ):
            app._begin_transcription(_audio())
            app._on_final_result(raw)
            if raw == "raw three":
                app._on_polish_error("network down")
            else:
                app._on_polish_complete(polished)
            h["paster"].paste_async.call_args[0][1]("pasted")

        records = _enqueued_records(h["history"])
        session_ids = {record.session_id for record in records}
        assert len(records) == 3
        assert len(session_ids) == 1
        assert "stale" not in session_ids
        assert [record.seq for record in records] == [0, 1, 2]
        assert [(r.raw_text, r.polished_text) for r in records] == [
            ("raw one", "polished one"),
            ("raw two", "polished two"),
            ("raw three", "raw three"),
        ]
        assert all(record.source == "mixed" for record in records)
        assert all(record.trigger_mode == "continuous" for record in records)
        assert all(record.model == "fire-red-asr2-ctc-zh_en-int8" for record in records)


def test_asr_error_auto_restart_keeps_continuous_session_id() -> None:
    with app_harness({"audio.trigger_mode": "continuous"}) as h:
        app = h["app"]
        _drive_segment(app, h["paster"], "before error")
        first_record = _enqueued_records(h["history"])[0]

        h["recorder"].is_continuous = False
        app._continuous_user_stopped = False
        app._on_recognizer_error("ASR crashed")
        _drive_segment(app, h["paster"], "after restart")

        records = _enqueued_records(h["history"])
        assert [record.seq for record in records] == [0, 1]
        assert records[1].session_id == first_record.session_id


def test_pending_paste_callback_freezes_segment_values_across_race() -> None:
    with app_harness({"audio.trigger_mode": "continuous"}) as h:
        app = h["app"]

        first_callback = _begin_and_finish_asr(app, h["paster"], "segment n")
        second_callback = _begin_and_finish_asr(app, h["paster"], "segment n plus one")

        first_callback("pasted")
        second_callback("pasted")

        records = _enqueued_records(h["history"])
        assert [record.raw_text for record in records] == ["segment n", "segment n plus one"]
        assert [record.seq for record in records] == [0, 1]


def test_history_disabled_skips_enqueue_and_mid_run_disable_affects_next_segment() -> None:
    with app_harness({"history.enabled": False}) as h:
        _drive_segment(h["app"], h["paster"], "disabled from start")
        h["history"].enqueue.assert_not_called()

    with app_harness() as h:
        _drive_segment(h["app"], h["paster"], "enabled segment")
        assert h["history"].enqueue.call_count == 1

        h["config"].set("history.enabled", False)
        _drive_segment(h["app"], h["paster"], "disabled segment")

        assert h["history"].enqueue.call_count == 1


def test_clipboard_and_error_paste_results_enqueue_history() -> None:
    with app_harness() as h:
        _drive_segment(h["app"], h["paster"], "copied text", result="clipboard")
        _drive_segment(h["app"], h["paster"], "failed text", result="error:target locked")

        records = _enqueued_records(h["history"])
        assert [record.raw_text for record in records] == ["copied text", "failed text"]
