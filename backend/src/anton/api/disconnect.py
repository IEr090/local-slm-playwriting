import asyncio
from collections.abc import Coroutine
from contextlib import suppress
from typing import Any, TypeVar

from fastapi import Request


T = TypeVar("T")


class ClientDisconnectedError(Exception):
    """Represent a request whose client left before the answer was ready."""


async def cancel_on_disconnect(request: Request, work: Coroutine[Any, Any, T]) -> T:
    """Run the work and cancel it as soon as the client disconnects, e.g. after pressing Cancel.

    Cancelling closes the connection to the model server, so the model stops generating too.
    """
    task = asyncio.create_task(work)
    watcher = asyncio.create_task(_wait_for_disconnect(request))
    try:
        await asyncio.wait({task, watcher}, return_when=asyncio.FIRST_COMPLETED)
    finally:
        watcher.cancel()
        if not task.done():
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    if task.cancelled():
        raise ClientDisconnectedError
    return task.result()


async def _wait_for_disconnect(request: Request) -> None:
    """Return when the client has closed the connection; the request body is already read by then."""
    while (await request.receive())["type"] != "http.disconnect":
        pass
