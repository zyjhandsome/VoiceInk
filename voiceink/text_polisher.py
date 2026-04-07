import logging
from PyQt6.QtCore import QObject, pyqtSignal, QThread

log = logging.getLogger("VoiceInk")

POLISH_PROMPT = (
    "你是一个纯文本润色工具，不是对话助手。\n"
    "你的唯一任务是：将用户发来的语音转写文字做最小程度的润色，使其变为通顺的书面语。\n\n"
    "严格规则：\n"
    "1. 绝对不要回答、回应或评论文字的内容，无论内容是问题、请求还是陈述。\n"
    "2. 只做最小修改：修正口语赘词（嗯、啊、那个、就是说）、补全标点、理顺语序。\n"
    "3. 保持原意和原有信息量完全不变，不要添加、删除或改写任何实质内容。\n"
    "4. 如果包含中英文混合，保持原有语言不变。\n"
    "5. 只输出润色后的文字本身，不要加引号、不要加前缀、不要做任何解释。\n\n"
    "示例：\n"
    "输入：嗯那个我觉得这个方案还行吧就是可能需要再优化一下\n"
    "输出：我觉得这个方案还行，可能需要再优化一下。\n\n"
    "输入：今天天气怎么样啊感觉还不错\n"
    "输出：今天天气怎么样？感觉还不错。"
)


class PolishWorker(QThread):
    result_ready = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, api_url: str, api_key: str, model_name: str, text: str,
                 prompt: str = ""):
        super().__init__()
        self._api_url = api_url.rstrip("/")
        self._api_key = api_key
        self._model_name = model_name
        self._text = text
        self._prompt = prompt or POLISH_PROMPT

    def run(self):
        try:
            import httpx

            url = self._api_url
            if not url.endswith("/chat/completions"):
                url = url.rstrip("/") + "/chat/completions"

            log.info("正在调用 LLM 润色 (%s)...", self._model_name)
            log.info("  原文: %s", self._text[:80])

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}"
            }

            payload = {
                "model": self._model_name,
                "messages": [
                    {"role": "system", "content": self._prompt},
                    {"role": "user", "content": self._text}
                ],
                "temperature": 0.3,
                "max_tokens": 2048
            }

            with httpx.Client(timeout=15.0) as client:
                response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()

            choices = data.get("choices")
            if not choices or not isinstance(choices, list):
                self.error.emit("润色失败: API 响应格式异常")
                return
            polished = choices[0].get("message", {}).get("content", "").strip()
            if not polished:
                self.error.emit("润色失败: API 返回空内容")
                return
            log.info("  润色结果: %s", polished[:80])
            self.result_ready.emit(polished)

        except httpx.TimeoutException:
            log.error("LLM 润色超时")
            self.error.emit("润色超时")
        except Exception as e:
            log.error("LLM 润色失败: %s", e)
            self.error.emit(f"润色失败: {str(e)}")


class TextPolisher(QObject):
    polish_complete = pyqtSignal(str)
    polish_error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None

    def polish(self, text: str, api_url: str, api_key: str, model_name: str,
               prompt: str = ""):
        if not text.strip():
            self.polish_complete.emit(text)
            return

        self.cancel()

        self._worker = PolishWorker(api_url, api_key, model_name, text, prompt)
        self._worker.result_ready.connect(self._on_result)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def cancel(self):
        """Wait for any running worker to finish (best-effort cleanup)."""
        if self._worker and self._worker.isRunning():
            self._worker.wait(3000)
        self._worker = None

    def _on_result(self, polished_text: str):
        self.polish_complete.emit(polished_text)

    def _on_error(self, error_msg: str):
        self.polish_error.emit(error_msg)

    @staticmethod
    def test_connection(api_url: str, api_key: str, model_name: str) -> tuple[bool, str]:
        try:
            import httpx

            url = api_url.rstrip("/")
            if not url.endswith("/chat/completions"):
                url = url.rstrip("/") + "/chat/completions"

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }

            payload = {
                "model": model_name,
                "messages": [
                    {"role": "user", "content": "Hello"}
                ],
                "max_tokens": 5
            }

            with httpx.Client(timeout=10.0) as client:
                response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()

            return True, "连接成功"
        except httpx.TimeoutException:
            return False, "连接超时"
        except httpx.HTTPStatusError as e:
            return False, f"HTTP 错误: {e.response.status_code}"
        except Exception as e:
            return False, f"连接失败: {str(e)}"
