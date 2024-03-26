import socket
import os
import time

class FTPSockerServer:
    CLIENT_PIDS = dict()
    class ClientHandler:
        def __init__(self, conn, addr, read_size=1024):
            self.conn = conn
            self.addr = addr
            self.read_size = read_size
            # add to set of clients
            FTPSockerServer.CLIENT_PIDS[os.getpid()] = -1
        
        def handle(self):            
            retry = 3
            while True:
                data = self.conn.recv(self.read_size).decode().strip()
                if not data:
                    if retry > 0:
                        time.sleep(1)
                        retry -= 1
                        continue
                    break
                print(f"Received data from {self.addr[0]}:{self.addr[1]}: {data}")
            self.conn.close()
            print(f"Connection from {self.addr[0]}:{self.addr[1]} closed")
            FTPSockerServer.CLIENT_PIDS[os.getpid()] = 0
            os._exit(0)
            # TODO : decode data and save to file

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    def start(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(1)
        print(f"FTP server listening on {self.host}:{self.port}")
        while True:
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