import asyncio
import threading
import queue
import websockets.server as wss

# Queue for outbound messages from LLDB
outgoing_q: queue.Queue[str] = queue.Queue()

# Store the single active client
client: wss.WebSocketServerProtocol | None = None


async def ws_handler(websocket: wss.WebSocketServerProtocol):
    """
    Accept a single client connection.
    If another connects, the previous one is dropped.
    """
    global client
    if client is not None:
        await client.close()
    client = websocket

    try:
        async for _ in websocket:
            # Ignoring incoming messages for now
            pass
    finally:
        if client is websocket:
            client = None


async def sender() -> None:
    """Forward queued messages to the active client."""
    global client
    loop = asyncio.get_event_loop()
    while True:
        msg = await loop.run_in_executor(None, outgoing_q.get)
        if client is not None:
            try:
                await client.send(msg)
            except Exception:
                client = None
        outgoing_q.task_done()


def run_server() -> None:
    """Run the websocket server inside its own event loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    server = wss.serve(ws_handler, "localhost", 8765)
    loop.run_until_complete(server)
    loop.create_task(sender())
    loop.run_forever()


def start_background() -> None:
    """Launch the server in a background thread."""
    t = threading.Thread(target=run_server, daemon=True)
    t.start()


def enqueue_message(msg: str) -> None:
    """Enqueue a message for the client."""
    outgoing_q.put(msg)
