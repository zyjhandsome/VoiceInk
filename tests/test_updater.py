"""GitHub release check: compare versions, pick the installer, respect the daily gate."""

from io import BytesIO

from voiceink.updater import (
    ReleaseInfo,
    download_installer,
    is_newer,
    is_trusted_installer_url,
    release_from_payload,
    should_auto_check,
)


def _payload(version: str, name: str, url: str) -> dict:
    return {
        "tag_name": f"v{version}",
        "assets": [{"name": name, "browser_download_url": url}],
    }


class TestReleaseSelection:
    def test_newer_release_with_the_matching_installer_is_offered(self):
        info = release_from_payload(
            _payload(
                "2.0.6",
                "VoiceInk-Setup-2.0.6.exe",
                "https://github.com/zyjhandsome/VoiceInk/releases/download/v2.0.6/VoiceInk-Setup-2.0.6.exe",
            ),
            current="2.0.5",
        )
        assert info == ReleaseInfo(
            version="2.0.6",
            asset_name="VoiceInk-Setup-2.0.6.exe",
            asset_url="https://github.com/zyjhandsome/VoiceInk/releases/download/v2.0.6/VoiceInk-Setup-2.0.6.exe",
        )

    def test_same_or_older_release_is_not_an_update(self):
        payload = _payload(
            "2.0.5",
            "VoiceInk-Setup-2.0.5.exe",
            "https://github.com/zyjhandsome/VoiceInk/releases/download/v2.0.5/VoiceInk-Setup-2.0.5.exe",
        )
        assert release_from_payload(payload, current="2.0.5") is None
        assert not is_newer("2.0.4", "2.0.5")

    def test_untrusted_asset_url_is_ignored(self):
        info = release_from_payload(
            _payload("9.0.0", "VoiceInk-Setup-9.0.0.exe", "http://example.com/setup.exe"),
            current="2.0.5",
        )
        assert info is None
        assert not is_trusted_installer_url("http://github.com/a.exe")


class TestAutoCheckGate:
    def test_disabled_switch_never_checks(self):
        assert should_auto_check(enabled=False, last_check_at=0, now=10_000) is False

    def test_first_check_and_daily_interval(self):
        assert should_auto_check(enabled=True, last_check_at=0, now=10_000) is True
        assert should_auto_check(enabled=True, last_check_at=1_000, now=1_000 + 3600) is False
        assert should_auto_check(enabled=True, last_check_at=1_000, now=1_000 + 86_400) is True


class TestDownload:
    def test_download_writes_the_body_and_reports_size(self, tmp_path):
        body = b"installer-bytes"

        class _Response:
            headers = {"Content-Length": str(len(body))}

            def read(self, _n):
                return self._buf.read(_n)

            def __enter__(self):
                self._buf = BytesIO(body)
                return self

            def __exit__(self, *args):
                return False

        seen = []
        dest = tmp_path / "VoiceInk-Setup-2.0.6.exe"
        download_installer(
            "https://github.com/zyjhandsome/VoiceInk/releases/download/v2.0.6/VoiceInk-Setup-2.0.6.exe",
            dest,
            lambda *_args, **_kwargs: _Response(),
            on_progress=lambda got, total: seen.append((got, total)),
        )
        assert dest.read_bytes() == body
        assert seen[-1] == (len(body), len(body))
