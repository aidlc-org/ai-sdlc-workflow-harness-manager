"""Provider protocol for agent-security collectors and inline evaluators."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from ..models import Decision, Finding, ProviderCapabilities, SecurityEvent


@runtime_checkable
class SecurityProvider(Protocol):
    """Optional-capability SPI. Implement only the methods you support."""

    def name(self) -> str: ...

    def capabilities(self) -> ProviderCapabilities: ...

    def health(self) -> list[dict[str, Any]]:
        """Return provider/source health records (no secrets)."""
        ...

    def evaluate(self, event: SecurityEvent) -> Decision | None:
        """Synchronous evaluation. Return None when the provider skips the event."""
        ...

    def collect(self, state_dir: Any, sources: tuple[str, ...] | list[str]) -> dict[str, Any]:
        """Asynchronous session collection. Return summary dict."""
        ...
