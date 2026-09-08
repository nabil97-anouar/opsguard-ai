"""Small error-summary boundary for persisted workflow diagnostics."""
import re

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.tools.hygiene import clean_text


def error_summary(error: Exception) -> str:
    if isinstance(error, SQLAlchemyError):
        return "Database operation failed."
    if isinstance(error, ValidationError):
        return "Structured data validation failed."
    # Preserve useful bounded domain errors, not credentials or connection URLs.
    message = re.sub(r"[a-z][a-z0-9+.-]*://[^\s]*@[^\s]+", "[REDACTED_CONNECTION]", str(error), flags=re.I)
    return clean_text(message)
