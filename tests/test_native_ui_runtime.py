"""Contracts for the WebEngine-free native settings/history runtime."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_runtime_has_no_webengine_dependency_or_bridge_modules():
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "WebEngine" not in requirements

    removed_modules = (
        "web_surface.py",
        "general_settings_web.py",
        "models_settings_web.py",
        "polish_settings_web.py",
        "about_settings_web.py",
        "history_web.py",
    )
    ui_dir = ROOT / "voiceink" / "ui"
    assert all(not (ui_dir / name).exists() for name in removed_modules)
    assert not (ui_dir / "web").exists()


def test_selected_html_surfaces_are_archived_as_prototypes():
    archive = ROOT / "prototypes" / "reference-html"
    assert {
        "history.html",
        "settings_about.html",
        "settings_general.html",
        "settings_models.html",
        "settings_polish.html",
    }.issubset({path.name for path in archive.glob("*.html")})
