"""Application errors mapped to the spec's JSON error statuses. No error carries a score."""


class AppError(Exception):
    status_code = 500
    code = "internal_error"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class TranscriptTooLarge(AppError):
    status_code = 413
    code = "transcript_too_large"


class ExtractionFailed(AppError):
    """Unusable, refused, or invalid-evidence extraction (502)."""

    status_code = 502
    code = "extraction_failed"


class ProviderUnavailable(AppError):
    """Provider unavailable or rate-limited (503)."""

    status_code = 503
    code = "provider_unavailable"


class ProviderTimeout(AppError):
    status_code = 504
    code = "timeout"


class ConfigurationError(AppError):
    """Missing or rejected server credentials (500)."""

    status_code = 500
    code = "configuration_error"
