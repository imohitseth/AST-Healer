"""
Stub for google.antigravity (Gemini agentic SDK).

This module is used in CI only. It raises a clear error if any code
tries to actually invoke the agent without a real API key, while allowing
all imports and module-level code to succeed.
"""


class _StubResponse:
    """Mimics the response object returned by Agent.generate_content()."""

    def __init__(self) -> None:
        self.text = "# STUB: no GEMINI_API_KEY set in CI"


class Agent:
    """
    Minimal stub for google.antigravity.Agent.

    Allows main.py and app.py to import cleanly in CI.
    Any test that actually calls .generate_content() must be marked
    @pytest.mark.requires_api_key and will be skipped when the key is absent.
    """

    def __init__(self, model: str = "", **kwargs) -> None:
        self._model = model

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args) -> None:
        pass

    def generate_content(self, prompt: str, **kwargs) -> _StubResponse:
        import os

        if not os.environ.get("GEMINI_API_KEY", "").strip():
            raise RuntimeError(
                "GEMINI_API_KEY is not set. "
                "This test requires a real API key — mark it with "
                "@pytest.mark.requires_api_key so it is skipped in CI."
            )
        raise NotImplementedError(
            "Real Gemini calls are not supported in the stub. "
            "Install google-antigravity for live runs."
        )
