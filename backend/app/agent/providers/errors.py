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


class ProviderAuthenticationError(ProviderError):
    public_message = "Reasoning provider rejected credentials or access permissions."


class ProviderRequestError(ProviderError):
    public_message = "Reasoning provider rejected the request. Check the API base URL, model and response-format configuration."


class ProviderRefusalError(ProviderInvalidOutputError):
    public_message = "Reasoning provider refused the request; no recommendation was accepted."


class ProviderTruncatedOutputError(ProviderInvalidOutputError):
    public_message = "Reasoning provider output was truncated; no partial recommendation was accepted."
