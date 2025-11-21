"""Reusable Playwright-powered validator for candidate URLs."""

from __future__ import annotations

import asyncio
import contextlib
import time
from typing import Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Playwright

from .models import ValidationResult, ValidationStatus


class BrowserValidator:
    """Manage a single Playwright browser/context reused across validations."""

    def __init__(self, headless: bool = True, timeout_ms: int = 15000):
        self._headless = headless
        self._timeout_ms = timeout_ms
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None

    async def _ensure_context(self) -> BrowserContext:
        if self._context is None:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=self._headless)
            self._context = await self._browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                ignore_https_errors=True,
            )
        return self._context

    async def close(self):
        """Close resources."""
        with contextlib.suppress(Exception):
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        self._context = None
        self._browser = None
        self._playwright = None

    async def validate_url(self, url: str, verbose: bool = False) -> ValidationResult:
        """Validate the given URL using a real browser."""
        page = None
        start = time.time()
        try:
            context = await self._ensure_context()
            page = await context.new_page()
            response = await page.goto(url, timeout=self._timeout_ms, wait_until="domcontentloaded")

            http_status = response.status if response else None
            final_url = page.url
            latency_ms = int((time.time() - start) * 1000)

            if response and 200 <= response.status < 400:
                status = ValidationStatus.OK
                if final_url and final_url.rstrip("/") != url.rstrip("/"):
                    status = ValidationStatus.REDIRECTED
            else:
                status = ValidationStatus.BLOCKED if http_status else ValidationStatus.ERROR

            return ValidationResult(
                status=status,
                http_status=http_status,
                final_url=final_url,
                latency_ms=latency_ms,
            )

        except Exception as exc:
            latency_ms = int((time.time() - start) * 1000)
            status = ValidationStatus.TIMEOUT if "Timeout" in str(exc) else ValidationStatus.ERROR
            return ValidationResult(
                status=status,
                error=str(exc),
                latency_ms=latency_ms,
            )
        finally:
            if page:
                with contextlib.suppress(Exception):
                    await page.close()

    def validate_url_sync(self, url: str, verbose: bool = False) -> ValidationResult:
        """Synchronous wrapper for validate_url."""
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(self.validate_url(url, verbose=verbose))
        finally:
            loop.run_until_complete(self.close())
            loop.close()


def validate_url_sync(url: str, timeout_ms: int = 15000, headless: bool = True) -> ValidationResult:
    """Convenience helper that spins up a temporary validator for a single URL."""
    validator = BrowserValidator(headless=headless, timeout_ms=timeout_ms)
    return validator.validate_url_sync(url)

