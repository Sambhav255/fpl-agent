"""Official adapter placeholders intentionally have no network implementation."""

from .records import Capability, Record


class ProviderStatus(Record):
    provider: str
    status: str = "unavailable"
    reason: str = "No permitted access; live collection is not implemented."
    live_fetch: bool = False


class DisabledOfficialAdapter:
    def __init__(self, provider: str) -> None:
        if provider not in ("reddit", "x"):
            raise ValueError("Only official Reddit and X placeholders are supported")
        self.capability = Capability(provider=provider, reference=f"{provider}-disabled")  # type: ignore[arg-type]

    def status(self) -> ProviderStatus:
        return ProviderStatus(provider=self.capability.provider)

    def fetch(self) -> None:
        raise PermissionError(self.status().reason)


class RedditAdapter(DisabledOfficialAdapter):
    def __init__(self) -> None:
        super().__init__("reddit")


class XAdapter(DisabledOfficialAdapter):
    def __init__(self) -> None:
        super().__init__("x")
