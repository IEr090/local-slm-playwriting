import asyncio
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase

from anton.api.disconnect import ClientDisconnectedError, cancel_on_disconnect


def make_request(disconnect: asyncio.Event) -> SimpleNamespace:
    """Create a request whose receive() reports a disconnect once the event is set."""

    async def receive() -> dict:
        await disconnect.wait()
        return {"type": "http.disconnect"}

    return SimpleNamespace(receive=receive)


class CancelOnDisconnectTest(IsolatedAsyncioTestCase):
    """Test cancelling work when the client leaves."""

    async def asyncSetUp(self) -> None:
        """Prepare a client that stays connected until the event is set."""
        self.disconnect = asyncio.Event()
        self.request = make_request(self.disconnect)
        self.cancelled = False

    async def slow_work(self) -> str:
        """Work that takes long and remembers whether it was cancelled."""
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            self.cancelled = True
            raise
        return "done"

    async def test_returns_result_while_client_stays(self) -> None:
        """Return the result of the work when the client waits for it."""
        async def work() -> str:
            return "cast"

        self.assertEqual(await cancel_on_disconnect(self.request, work()), "cast")

    async def test_passes_errors_of_the_work_through(self) -> None:
        """Raise the error of the work so the error handlers can answer it."""
        async def work() -> str:
            raise ValueError("model failed")

        with self.assertRaisesRegex(ValueError, "model failed"):
            await cancel_on_disconnect(self.request, work())

    async def test_cancels_work_when_client_leaves(self) -> None:
        """Cancel the work and report the disconnect."""
        asyncio.get_running_loop().call_later(0.01, self.disconnect.set)

        with self.assertRaises(ClientDisconnectedError):
            await asyncio.wait_for(cancel_on_disconnect(self.request, self.slow_work()), timeout=1)
        self.assertTrue(self.cancelled)

    async def test_cancels_work_when_request_is_cancelled(self) -> None:
        """Cancel the work when the server cancels the request, e.g. on shutdown."""
        pending = asyncio.create_task(cancel_on_disconnect(self.request, self.slow_work()))
        await asyncio.sleep(0.01)
        pending.cancel()

        with self.assertRaises(asyncio.CancelledError):
            await pending
        self.assertTrue(self.cancelled)
