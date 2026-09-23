"""Keep the LLM API key in Windows Credential Manager instead of config.json."""

from __future__ import annotations

import logging
import sys

log = logging.getLogger("VoiceInk")

CREDENTIAL_TARGET = "VoiceInk/llm.api_key"


class WindowsCredentialStore:
    """Generic credential scoped to the current Windows user."""

    def __init__(self, target: str = CREDENTIAL_TARGET):
        import win32cred

        self._cred = win32cred
        self._target = target

    def read(self) -> str | None:
        try:
            cred = self._cred.CredRead(self._target, self._cred.CRED_TYPE_GENERIC, 0)
        except Exception as exc:
            if getattr(exc, "winerror", None) == 1168:  # ERROR_NOT_FOUND
                return ""
            log.warning("读取凭据管理器失败: %s", exc)
            return None
        blob = cred.get("CredentialBlob") or b""
        if isinstance(blob, bytes):
            return blob.decode("utf-16-le", errors="ignore")
        return str(blob)

    def write(self, value: str) -> bool:
        try:
            if not value:
                try:
                    self._cred.CredDelete(self._target, self._cred.CRED_TYPE_GENERIC, 0)
                except Exception as exc:
                    if getattr(exc, "winerror", None) != 1168:
                        raise
                return True
            self._cred.CredWrite(
                {
                    "Type": self._cred.CRED_TYPE_GENERIC,
                    "TargetName": self._target,
                    "UserName": "VoiceInk",
                    "CredentialBlob": value,
                    "Persist": self._cred.CRED_PERSIST_LOCAL_MACHINE,
                },
                0,
            )
            return True
        except Exception as exc:
            log.warning("写入凭据管理器失败: %s", exc)
            return False


def default_secret_store():
    if sys.platform != "win32":
        return None
    try:
        return WindowsCredentialStore()
    except Exception as exc:
        log.warning("凭据管理器不可用: %s", exc)
        return None
