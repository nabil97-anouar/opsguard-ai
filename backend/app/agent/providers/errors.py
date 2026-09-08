"""Stable provider failures safe to surface through workflow traces."""


class ProviderError(RuntimeError):
    public_message = "Reasoning provider failed."

    def __init__(self, diagnostic: str | None = None) -> None:
        super().__init__(self.public_message)
        self.diagnostic = diagnostic


class ProviderConfigurationError(ProviderError):
    public_message = "Reasoning provider configuration is invalid."


class ProviderTimeoutError(ProviderError):
    public_message = "Reasoning provider timed out."


class ProviderUnavailableError(ProviderError):
    public_message = "Reasoning provider is unavailable."


class ProviderRateLimitError(ProviderError):
    public_message = "Reasoning provider rate limit was reached."


class ProviderInvalidOutputError(ProviderError):
    public_message = "Reasoning provider returned invalid structured output."
