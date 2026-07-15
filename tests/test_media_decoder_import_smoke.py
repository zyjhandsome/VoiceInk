"""Quick smoke: media_decoder public API remains importable."""

from voiceink.media_decoder import (
    CancelledError,
    DecodeError,
    MissingFFmpegError,
    NoAudioError,
    decode_media_to_pcm,
    resolve_ffmpeg_executable,
)


def test_public_api_symbols_are_importable():
    assert callable(resolve_ffmpeg_executable)
    assert callable(decode_media_to_pcm)
    for exc in (MissingFFmpegError, DecodeError, NoAudioError, CancelledError):
        assert issubclass(exc, Exception)
