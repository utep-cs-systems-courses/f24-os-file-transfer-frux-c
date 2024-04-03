# !/usr/bin/env python3
# Description: FTP server that listens on a given port and saves files sent by clients
import socket
import os
import time
from lib.framer import OutbandFramer

class FTPSockerServer:

    CLIENT_PIDS = dict()
    
    class ClientHandler:
        def __init__(self, conn, addr, read_size=1024):
            self.conn = conn
            self.addr = addr
            self.read_size = read_size
        
        def handle(self):            
            retry = 3
            data = b''
            while True:
                incoming_data = self.conn.recv(self.read_size)
                if not incoming_data:
                    if retry > 0:
                        retry -= 1
                        continue
                    break
                data += incoming_data
            try:
                fname_n_data = OutbandFramer(1024, 64, b'\\').unframe_data(data)
                for fname, fdata in fname_n_data:
                    print("Received file:", fname)
                    fd = os.open(fname, os.O_CREAT | os.O_WRONLY)
                    os.write(fd, fdata)
                    os.close(fd)
            except Exception as e:
                print(f"Error: {e}")
                self.conn.close()
                self.conn.shutdown(socket.SHUT_RDWR)
                print(f"Connection from {self.addr[0]}:{self.addr[1]} closed")
                os._exit(1)
            print(f"Connection from {self.addr[0]}:{self.addr[1]} closed")
            os._exit(0)

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.running = True
    
    def start(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(1)
        print(f"FTP server listening on {self.host}:{self.port}")

        while self.running:
            conn, addr = self.server_socket.accept()
            print(f"Accepted connection from {addr[0]}:{addr[1]}")
            pid = os.fork()
            if pid == 0:
                client_handler = self.ClientHandler(conn, addr)
                client_handler.handle()
            

    def stop(self):
        # currently not used
        self.server_socket.close()


if __name__ == '__main__':
    ftp_server = FTPSockerServer('localhost', 8001)
    ftp_server.start()