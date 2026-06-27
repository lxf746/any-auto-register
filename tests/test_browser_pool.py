"""Tests for BrowserPool - reusable asyncio.Queue-based browser context pool."""
import asyncio
from unittest.mock import AsyncMock
from core.turnstile_pool import BrowserPool


def test_empty_pool_qsize():
    """Empty pool should have qsize 0."""
    async def run():
        pool = BrowserPool(max_size=3)
        assert pool.qsize() == 0
        await pool.close()
    asyncio.run(run())


def test_acquire_returns_context():
    """acquire() returns a context from create_context_fn."""
    async def run():
        mock_ctx = AsyncMock()
        create_fn = AsyncMock(return_value=mock_ctx)
        pool = BrowserPool(max_size=3, create_context_fn=create_fn)
        ctx = await pool.acquire()
        assert ctx is mock_ctx
        assert pool.qsize() == 0
        await pool.close()
    asyncio.run(run())


def test_release_returns_to_pool():
    """release() puts context back in pool."""
    async def run():
        mock_ctx = AsyncMock()
        create_fn = AsyncMock(return_value=mock_ctx)
        pool = BrowserPool(max_size=3, create_context_fn=create_fn)
        ctx = await pool.acquire()
        await pool.release(ctx)
        assert pool.qsize() == 1
        await pool.close()
    asyncio.run(run())


def test_acquire_reuses_released_context():
    """acquire() reuses a previously released context."""
    async def run():
        mock_ctx = AsyncMock()
        create_fn = AsyncMock(return_value=mock_ctx)
        pool = BrowserPool(max_size=3, create_context_fn=create_fn)
        ctx1 = await pool.acquire()
        await pool.release(ctx1)
        ctx2 = await pool.acquire()
        assert ctx1 is ctx2
        await pool.close()
    asyncio.run(run())


def test_acquire_creates_new_when_empty():
    """acquire() creates new context when pool is empty."""
    async def run():
        call_count = 0

        async def create_fn():
            nonlocal call_count
            call_count += 1
            return AsyncMock()

        pool = BrowserPool(max_size=3, create_context_fn=create_fn)
        ctx1 = await pool.acquire()
        ctx2 = await pool.acquire()
        assert ctx1 is not ctx2
        assert call_count == 2
        await pool.close()
    asyncio.run(run())


def test_acquire_respects_max_size():
    """acquire() waits when at max_size and all contexts are out."""
    async def run():
        create_fn = AsyncMock(side_effect=AsyncMock)
        pool = BrowserPool(max_size=2, create_context_fn=create_fn)

        ctx1 = await pool.acquire()
        ctx2 = await pool.acquire()
        assert pool.qsize() == 0

        # Third acquire should block
        async def try_acquire():
            return await pool.acquire()

        try:
            await asyncio.wait_for(try_acquire(), timeout=0.1)
            assert False, "Should have timed out"
        except asyncio.TimeoutError:
            pass  # Expected - pool is full

        await pool.release(ctx1)
        ctx3 = await pool.acquire()
        assert ctx3 is ctx1
        await pool.close()
    asyncio.run(run())


def test_close_drains_pool():
    """close() closes all pooled contexts."""
    async def run():
        ctx1 = AsyncMock()
        ctx2 = AsyncMock()
        create_fn = AsyncMock(side_effect=[ctx1, ctx2])

        pool = BrowserPool(max_size=3, create_context_fn=create_fn)
        c1 = await pool.acquire()
        c2 = await pool.acquire()
        await pool.release(c1)
        await pool.release(c2)

        await pool.close()
        ctx1.aclose.assert_called_once()
        ctx2.aclose.assert_called_once()
    asyncio.run(run())


def test_close_handles_already_closed():
    """close() handles contexts that are already closed."""
    async def run():
        mock_ctx = AsyncMock()
        create_fn = AsyncMock(return_value=mock_ctx)
        pool = BrowserPool(max_size=3, create_context_fn=create_fn)
        ctx = await pool.acquire()
        await pool.release(ctx)
        await pool.close()
        await pool.close()  # Should not raise
    asyncio.run(run())


def test_active_count_tracking():
    """_active_count tracks number of acquired (not pooled) contexts."""
    async def run():
        mock_ctx = AsyncMock()
        create_fn = AsyncMock(return_value=mock_ctx)
        pool = BrowserPool(max_size=3, create_context_fn=create_fn)
        assert pool._active_count == 0

        ctx = await pool.acquire()
        assert pool._active_count == 1

        await pool.release(ctx)
        assert pool._active_count == 0

        await pool.close()
    asyncio.run(run())
