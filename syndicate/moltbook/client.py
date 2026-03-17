"""
Moltbook API client — handles authentication, posting, captcha solving, and commenting.

Base URL: https://www.moltbook.com/api/v1
Auth: Bearer token via MOLTBOOK_API_KEY

Every post/comment triggers a captcha (lobster-themed math problem).
The client solves these automatically.
"""

from __future__ import annotations

import re
import time
from typing import Any

import httpx
import structlog

logger = structlog.get_logger()

BASE_URL = "https://www.moltbook.com/api/v1"

# Default submolts for different content types
SUBMOLT_MARKET = "general"       # Market commentary, fund updates
SUBMOLT_AGENTS = "agents"        # AI agent discussions (no crypto!)
SUBMOLT_INFRA = "infrastructure" # Technical/infra posts

# Word-to-number mapping for Moltbook's lobster math captchas
_WORD_NUMBERS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
    "seventy": 70, "eighty": 80, "ninety": 90, "hundred": 100,
    "thousand": 1000, "million": 1_000_000,
}


def _solve_captcha(challenge_text: str) -> str:
    """
    Solve Moltbook's lobster math captcha.

    These are styled like:
      "A lOoBbSstTeRr swims with a claw force of thirty five neutons,
       and it gains twelve neutons from a dominance fight,
       how much total force?"

    Strategy: normalize text, extract all numbers (word or digit), and sum them.
    """
    # Normalize: lowercase, collapse weird capitalization
    text = challenge_text.lower()
    # Remove special chars except hyphens (for compound numbers like "thirty-five")
    text = re.sub(r"[^a-z0-9\s\-.]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    numbers: list[float] = []

    # Extract digit-based numbers
    for match in re.finditer(r"\b(\d+(?:\.\d+)?)\b", text):
        numbers.append(float(match.group(1)))

    # Extract word-based numbers
    words = text.replace("-", " ").split()
    i = 0
    while i < len(words):
        word = words[i]
        if word in _WORD_NUMBERS:
            value = _WORD_NUMBERS[word]
            # Handle compound: "thirty five" = 30 + 5
            if value >= 20 and value < 100 and i + 1 < len(words) and words[i + 1] in _WORD_NUMBERS:
                next_val = _WORD_NUMBERS[words[i + 1]]
                if next_val < 10:
                    value += next_val
                    i += 1
            # Handle "hundred": "five hundred" = 5 * 100
            if i + 1 < len(words) and words[i + 1] == "hundred":
                value *= 100
                i += 1
                # "five hundred twelve" = 500 + 12
                if i + 1 < len(words) and words[i + 1] in _WORD_NUMBERS:
                    value += _WORD_NUMBERS[words[i + 1]]
                    i += 1
            numbers.append(float(value))
        i += 1

    # Determine operation from context
    if any(kw in text for kw in ["total", "sum", "combined", "plus", "gains", "adds", "more"]):
        result = sum(numbers)
    elif any(kw in text for kw in ["difference", "minus", "loses", "less", "subtract"]):
        result = numbers[0] - sum(numbers[1:]) if len(numbers) > 1 else numbers[0]
    elif any(kw in text for kw in ["product", "times", "multiplied"]):
        result = 1.0
        for n in numbers:
            result *= n
    elif any(kw in text for kw in ["divided", "ratio", "per"]):
        result = numbers[0] / numbers[1] if len(numbers) > 1 and numbers[1] != 0 else numbers[0]
    else:
        # Default to sum
        result = sum(numbers)

    answer = f"{result:.2f}"
    logger.debug("captcha_solved", challenge=challenge_text[:80], answer=answer, numbers=numbers)
    return answer


class MoltbookClient:
    """HTTP client for the Moltbook API with automatic captcha solving."""

    def __init__(self, api_key: str, timeout: float = 30.0) -> None:
        if not api_key:
            raise ValueError("MOLTBOOK_API_KEY is required")
        self._api_key = api_key
        self._timeout = timeout
        self._last_request_at = 0.0
        self._min_interval = 2.0  # seconds between requests (rate limit safety)

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _throttle(self) -> None:
        """Simple rate-limit throttle — wait if we're posting too fast."""
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_at = time.monotonic()

    def _solve_verification(self, data: dict[str, Any]) -> bool:
        """
        If the API response contains a verification challenge, solve it.

        Returns True if verified (or no challenge), False on failure.
        """
        # Check nested structures for verification data
        verification = None
        if "verification" in data:
            verification = data["verification"]
        elif "post" in data and isinstance(data["post"], dict):
            verification = data["post"].get("verification")

        if not verification:
            return True  # No captcha needed

        challenge = verification.get("challenge_text", "")
        code = verification.get("verification_code", "")
        if not challenge or not code:
            return True

        answer = _solve_captcha(challenge)
        logger.info("moltbook_captcha_solving", code=code[:30], answer=answer)

        self._throttle()
        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.post(
                    f"{BASE_URL}/verify",
                    headers=self._headers,
                    json={"verification_code": code, "answer": answer},
                )
            if resp.status_code in (200, 201):
                result = resp.json()
                if result.get("success"):
                    logger.info("moltbook_captcha_verified", code=code[:30])
                    return True
                else:
                    logger.warning("moltbook_captcha_rejected", response=result)
                    return False
            else:
                logger.error("moltbook_captcha_failed", status=resp.status_code, body=resp.text[:200])
                return False
        except httpx.HTTPError as e:
            logger.error("moltbook_captcha_error", error=str(e))
            return False

    def create_post(
        self,
        title: str,
        content: str,
        submolt: str = SUBMOLT_MARKET,
    ) -> dict[str, Any]:
        """
        Create a post on Moltbook, automatically solving the captcha.

        Args:
            title: Post title (10-120 chars).
            content: Post body (plain text, emojis, limited markdown).
            submolt: Target submolt (default: 'general').

        Returns:
            API response dict with post id, title, content, created_at, etc.

        Raises:
            MoltbookAPIError: On non-2xx responses or captcha failure.
        """
        # Enforce title length limits
        title = title[:120]
        if len(title) < 10:
            title = title.ljust(10, ".")

        self._throttle()
        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.post(
                    f"{BASE_URL}/posts",
                    headers=self._headers,
                    json={
                        "submolt": submolt,
                        "title": title,
                        "content": content,
                    },
                )
            if resp.status_code in (200, 201):
                data = resp.json()

                # Solve captcha if present
                verified = self._solve_verification(data)
                if not verified:
                    logger.warning("moltbook_post_unverified", title=title[:60])

                post_id = data.get("post", {}).get("id") or data.get("id")
                logger.info(
                    "moltbook_post_created",
                    post_id=post_id,
                    title=title[:60],
                    submolt=submolt,
                    verified=verified,
                )
                return data
            else:
                logger.error(
                    "moltbook_post_failed",
                    status=resp.status_code,
                    body=resp.text[:500],
                )
                raise MoltbookAPIError(resp.status_code, resp.text)
        except httpx.HTTPError as e:
            logger.error("moltbook_request_error", error=str(e))
            raise MoltbookAPIError(0, str(e)) from e

    def create_comment(
        self,
        post_id: str,
        content: str,
        parent_id: str | None = None,
    ) -> dict[str, Any]:
        """Comment on a Moltbook post, automatically solving the captcha."""
        self._throttle()
        body: dict[str, str] = {"content": content}
        if parent_id:
            body["parent_id"] = parent_id
        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.post(
                    f"{BASE_URL}/posts/{post_id}/comments",
                    headers=self._headers,
                    json=body,
                )
            if resp.status_code in (200, 201):
                data = resp.json()
                self._solve_verification(data)
                logger.info("moltbook_comment_created", post_id=post_id)
                return data
            else:
                logger.error(
                    "moltbook_comment_failed",
                    status=resp.status_code,
                    body=resp.text[:500],
                )
                raise MoltbookAPIError(resp.status_code, resp.text)
        except httpx.HTTPError as e:
            logger.error("moltbook_comment_error", error=str(e))
            raise MoltbookAPIError(0, str(e)) from e

    def upvote(self, post_id: str) -> dict[str, Any]:
        """Upvote a Moltbook post."""
        self._throttle()
        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.post(
                    f"{BASE_URL}/posts/{post_id}/upvote",
                    headers=self._headers,
                )
            if resp.status_code in (200, 201):
                return resp.json()
            else:
                raise MoltbookAPIError(resp.status_code, resp.text)
        except httpx.HTTPError as e:
            raise MoltbookAPIError(0, str(e)) from e


class MoltbookAPIError(Exception):
    """Raised on Moltbook API errors."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"Moltbook API error {status_code}: {message[:200]}")
