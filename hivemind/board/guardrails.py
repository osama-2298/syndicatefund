"""
Prompt guardrails — validates Board-written prompts before deployment.

Ensures prompts meet minimum quality standards:
- Minimum/maximum length
- Required sections (conviction calibration, invalidation criteria)
- No hardcoded trading rules or specific price levels
"""

from __future__ import annotations

import structlog

from hivemind.board.prompt_templates import BANNED_PATTERNS, REQUIRED_PROMPT_SECTIONS

logger = structlog.get_logger()

MIN_PROMPT_LENGTH = 200
MAX_PROMPT_LENGTH = 2000


class PromptValidationError(Exception):
    """Raised when a Board-written prompt fails validation."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__(f"Prompt validation failed: {'; '.join(errors)}")


def validate_prompt(prompt: str) -> list[str]:
    """
    Validate a Board-written system prompt.
    Returns a list of errors (empty = valid).
    """
    errors: list[str] = []

    # Length checks
    if len(prompt) < MIN_PROMPT_LENGTH:
        errors.append(
            f"Prompt too short ({len(prompt)} chars, minimum {MIN_PROMPT_LENGTH}). "
            "Must include conviction calibration and invalidation criteria."
        )
    if len(prompt) > MAX_PROMPT_LENGTH:
        errors.append(
            f"Prompt too long ({len(prompt)} chars, maximum {MAX_PROMPT_LENGTH}). "
            "Be concise — agents work better with focused instructions."
        )

    # Required sections
    prompt_lower = prompt.lower()
    for section in REQUIRED_PROMPT_SECTIONS:
        if section not in prompt_lower:
            errors.append(
                f"Missing required section: '{section}'. "
                f"Prompts must include guidance on {section}."
            )

    # Banned patterns
    for pattern in BANNED_PATTERNS:
        if pattern.lower() in prompt_lower:
            errors.append(
                f"Contains banned pattern: '{pattern}'. "
                "Prompts must not contain hardcoded trading rules or specific price levels."
            )

    return errors


def validate_or_raise(prompt: str) -> None:
    """Validate a prompt and raise PromptValidationError if invalid."""
    errors = validate_prompt(prompt)
    if errors:
        logger.warning("prompt_validation_failed", errors=errors)
        raise PromptValidationError(errors)


def validate_data_keys(data_keys: list[str], available_keys: set[str]) -> list[str]:
    """Validate that all requested data keys exist in the data resolver registry."""
    errors = []
    for key in data_keys:
        if key not in available_keys:
            errors.append(f"Unknown data key: '{key}'. Available: {sorted(available_keys)}")
    return errors
