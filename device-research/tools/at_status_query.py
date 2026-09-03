"""Send read-only AT status queries to an OpenStick WWAN AT port."""

import os
import select
import sys
import termios
import time


port = sys.argv[1]
queries = ["AT", "AT+CPIN?", "AT+CFUN?", "AT+CSMINS?"]
fd = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
attrs = termios.tcgetattr(fd)
attrs[0] = 0
attrs[1] = 0
attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
attrs[3] = 0
attrs[4] = termios.B115200
attrs[5] = termios.B115200
termios.tcsetattr(fd, termios.TCSANOW, attrs)
termios.tcflush(fd, termios.TCIOFLUSH)

for query in queries:
    os.write(fd, (query + "\r").encode("ascii"))
    deadline = time.monotonic() + 2
    chunks = []
    while time.monotonic() < deadline:
        ready, _, _ = select.select([fd], [], [], 0.2)
        if ready:
            try:
                chunks.append(os.read(fd, 4096))
            except BlockingIOError:
                pass
    response = b"".join(chunks).decode("ascii", errors="replace").strip()
    print(f"[{port}] {query}\n{response or '<no response>'}")

os.close(fd)

