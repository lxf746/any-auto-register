"""Reusable browser context pool using asyncio.Queue pattern.

Extends the turnstile solver's asyncio.Queue pooling to a general-purpose
``BrowserPool`` class that any component can use for managing Playwright
browser contexts.

Usage::

    pool = BrowserPool(max_size=5, create_context_fn=browser.new_context)
    ctx = await pool.acquire()
    try:
        # use ctx ...
    finally:
        await pool.release(ctx)

    await pool.close()  # drain and close all contexts
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Awaitable, Optional

logger = logging.getLogger(__name__)


class BrowserPool:
    """Asyncio.Queue-based pool for browser contexts.

    Parameters
    ----------
    max_size:
        Maximum number of contexts that may exist simultaneously.
    create_context_fn:
        An async callable ``(no args) -> context`` used to create new contexts
        when the pool is empty and the count is below *max_size*.
    """

    def __init__(
        self,
        max_size: int = 5,
        create_context_fn: Optional[Callable[[], Awaitable[Any]]] = None,
    ) -> None:
        self._max_size = max_size
        self._create_context_fn = create_context_fn
        self._queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=max_size)
        self._count = 0  # total contexts created (pooled + in-use)
        self._active_count = 0  # contexts currently acquired (not in pool)
        self._closed = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def acquire(self) -> Any:
        """Acquire a browser context.

        If a previously released context is available in the pool it is reused.
        Otherwise a new context is created (up to *max_size*).  When the pool is
        at capacity and all contexts are out, this call **blocks** until one is
        released back.
        """
        if self._closed:
            raise RuntimeError("Cannot acquire from a closed BrowserPool")

        # Try to get an existing context from the pool first
        try:
            ctx = self._queue.get_nowait()
            self._active_count += 1
            return ctx
        except asyncio.QueueEmpty:
            pass

        # Pool is empty — create a new one if we haven't hit max_size
        if self._count < self._max_size:
            if self._create_context_fn is None:
                raise RuntimeError("create_context_fn not set and pool is empty")
            ctx = await self._create_context_fn()
            self._count += 1
            self._active_count += 1
            logger.debug(
                "BrowserPool: created context %d/%d", self._count, self._max_size
            )
            return ctx

        # At capacity — block until someone releases a context
        ctx = await self._queue.get()
        self._active_count += 1
        return ctx

    async def release(self, ctx: Any) -> None:
        """Return a context to the pool for reuse."""
        if self._closed:
            await self._safe_close(ctx)
            return

        self._active_count = max(0, self._active_count - 1)
        try:
            self._queue.put_nowait(ctx)
        except asyncio.QueueFull:
            # Should not happen, but handle gracefully
            await self._safe_close(ctx)
            self._count = max(0, self._count - 1)

    async def close(self) -> None:
        """Drain the pool and close all pooled contexts."""
        self._closed = True

        # Close all contexts remaining in the queue
        while not self._queue.empty():
            try:
                ctx = self._queue.get_nowait()
                await self._safe_close(ctx)
            except asyncio.QueueEmpty:
                break

        self._count = 0
        self._active_count = 0

    def qsize(self) -> int:
        """Return the number of contexts currently sitting in the pool (not acquired)."""
        return self._queue.qsize()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _safe_close(self, ctx: Any) -> None:
        """Close a context, suppressing errors."""
        try:
            if hasattr(ctx, "aclose"):
                await ctx.aclose()
            elif hasattr(ctx, "close"):
                result = ctx.close()
                if asyncio.iscoroutine(result):
                    await result
        except Exception as exc:
            logger.debug("BrowserPool: error closing context: %s", exc)
