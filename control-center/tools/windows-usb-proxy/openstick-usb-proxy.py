#!/usr/bin/env python3
"""Expose Clash's local HTTP proxy only to the OpenStick USB subnet."""

import select
import socket
import socketserver

LISTEN_ADDRESS = ("192.168.137.1", 17897)
TARGET_ADDRESS = ("127.0.0.1", 7897)


class ProxyHandler(socketserver.BaseRequestHandler):
    def handle(self):
        with socket.create_connection(TARGET_ADDRESS, timeout=10) as upstream:
            sockets = (self.request, upstream)
            while True:
                readable, _, _ = select.select(sockets, (), (), 30)
                if not readable:
                    continue
                for source in readable:
                    payload = source.recv(65536)
                    if not payload:
                        return
                    target = upstream if source is self.request else self.request
                    target.sendall(payload)


class ThreadedProxy(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    with ThreadedProxy(LISTEN_ADDRESS, ProxyHandler) as server:
        print(
            "OpenStick USB proxy: "
            f"{LISTEN_ADDRESS[0]}:{LISTEN_ADDRESS[1]} -> "
            f"{TARGET_ADDRESS[0]}:{TARGET_ADDRESS[1]}"
        )
        server.serve_forever()
