"""Stand-in for a wedged SSR service: accepts connections and never answers.

A dead SSR process refuses connections, which the library already survives
(``ConnectionError`` → client shell). A hung one — event-loop stall, OOM
thrash — completes the TCP handshake and then sends nothing, so only
``INERTIA_SSR_TIMEOUT`` bounds the render call. The ``ssr_unresponsive``
compose service runs this for the gevent E2E target.
"""

import os
import socket

port = int(os.getenv("NODE_PORT", "13714"))
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(("0.0.0.0", port))
server.listen(128)
print(f"unresponsive SSR stub listening on :{port}", flush=True)

held = []
while True:
    connection, _ = server.accept()
    # Keep a reference so the socket stays open; never read, never reply.
    held.append(connection)
