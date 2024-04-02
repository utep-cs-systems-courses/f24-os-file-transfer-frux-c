#! /usr/bin/env python3
# Description: This is the client side of the FTP application. It sends the file names to the server.
import socket
import os
from lib.framer import OutbandFramer
import sys

class FTPSocketClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        for res in socket.getaddrinfo(self.host, self.port, socket.AF_UNSPEC, socket.SOCK_STREAM):
            af, socktype, proto, canonname, sa = res
            try:
                self.client_socket = socket.socket(af, socktype, proto)
            except socket.error as msg:
                sys.stderr.write(f" error:{msg}\n")
                sys.stderr.flush()
                self.client_socket = None
                continue
            try:
                self.client_socket.connect(sa)
            except socket.error as msg:
                sys.stderr.write(f" error:{msg}\n")
                sys.stderr.flush()
                self.client_socket.close()
                self.client_socket = None
                continue
            break
        self.framer = OutbandFramer(1024, 64, '\\')
    
    def send(self, file_names):
        data = self.framer.frame_data(file_names, [os.open(fname, os.O_RDONLY) for fname in file_names])
        self.client_socket.send(data)
        self.close()

    def close(self):
        self.client_socket.shutdown(socket.SHUT_WR)
        self.client_socket.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.stderr.write(f"Usage: {sys.argv[0]} <host> <port> <file1> <file2> ...\n")
        sys.stderr.flush()
        sys.exit(1)
    host = sys.argv[1]
    port = int(sys.argv[2])
    files = sys.argv[3:]
    client = FTPSocketClient(host, port)
    client.send(files)