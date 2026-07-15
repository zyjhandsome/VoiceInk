"""Tests: ffmpeg bundling helpers must be removed from build.py."""

from __future__ import annotations

import build as build_mod


def test_build_has_no_ffmpeg_bundle_helpers():
    assert not hasattr(build_mod, "_ffmpeg_binary_name")
    assert not hasattr(build_mod, "_find_ffmpeg_bundle_source")
    assert not hasattr(build_mod, "_copy_ffmpeg_into_dist")
