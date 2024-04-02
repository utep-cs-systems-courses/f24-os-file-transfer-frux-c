#!/usr/bin/env python3
from __future__ import annotations
import os
import sys
from typing import TextIO, BinaryIO, IO, List, Tuple

class BufferedFdReader:

    def __init__(self, fd, bufLen = 1024*16):
        self.fd = fd
        self.buf = b""
        self.index = 0
        self.bufLen = bufLen

    def readByte(self):
        if self.index >= len(self.buf):
            self.buf = os.read(self.fd, self.bufLen)
            self.index = 0
        if len(self.buf) == 0:
            return None
        else:
            retval = self.buf[self.index]
            self.index += 1
            return retval
        
    def close(self):
        os.close(self.fd)

class BufferedFdWriter:

    def __init__(self, fd, bufLen = 1024*16):
        self.fd = fd
        self.buf = bytearray(bufLen)
        self.index = 0

    def writeByte(self, bVal):
        self.buf[self.index] = bVal
        self.index += 1
        if self.index >= len(self.buf):
            self.flush()

    def flush(self):
        startIndex, endIndex = 0, self.index
        while startIndex < endIndex:
            nWritten = os.write(self.fd, self.buf[startIndex:endIndex])
            if nWritten == 0:
                os.write(2,f"buf.BufferedFdWriter(fd={self.fd}): flush failed\n".encode())
                sys.exit(1)
            startIndex += nWritten
        self.index = 0

    def close(self):
        self.flush()
        os.close(self.fd)

class Framer:
    def __init__(self, frame_size: int, header_size: int):
        self.frame_size = frame_size
        self.header_size = header_size

    def create_header(self, info: bytes) -> bytes:
        arr = [b'\x00'] * self.header_size
        for i, val in enumerate(info):
            arr[i] = val.to_bytes(length=1, byteorder='big')
        return b''.join(arr)

    def frame_data(self, file_names: List[str], fds: List[int]) -> any:
        raise NotImplementedError
    
    def unframe_data(self, data: bytes) -> any:
        raise NotImplementedError
    

class InbandFramer(Framer):
    def __init__(self, frame_size: int, header_size: int, escape_byte: bytes, terminator_byte: bytes):
        super().__init__(frame_size, header_size)
        self.escape_byte = escape_byte
        self.termintor_byte = terminator_byte

    def frame_data(self, file_names: List[str], fds: List[int]) -> bytes:
        data = b''
        for file_name, fd in zip(file_names, fds):
            file_name = os.path.basename(file_name)
            file_name = self.create_header(file_name.encode('utf-8'))
            reader = BufferedFdReader(fd)
            data += file_name
            while (bt := reader.readByte()) is not None:
                bt = bt.to_bytes(length=1, byteorder='big')
                if bt == self.escape_byte:
                    data += self.escape_byte + self.escape_byte
                else:
                    data += bt
            data += self.escape_byte + self.termintor_byte
        return data

    def unframe_data(self, data: bytes) -> List[Tuple[str, bytes]]:
        headers = []
        payloads = []
        while data:
            header = data[:self.header_size]
            data = data[self.header_size:]
            payload = b''
            while data:
                if data[0:1] == self.escape_byte:
                    if data[1:2] == self.termintor_byte:
                        data = data[2:]
                        break
                    elif data[1:2] == self.escape_byte:
                        payload += self.escape_byte
                        data = data[2:]
                        continue
                payload += data[:1]
                data = data[1:]
            headers.append(header)
            payloads.append(payload)
        return [(header.decode().strip('\x00'), payload) for header, payload in zip(headers, payloads)]
    

class OutbandFramer(Framer):
    def __init__(self, frame_size: int, header_size: int, escape_byte: int):
        super().__init__(frame_size, header_size)
        self.escape_byte = escape_byte

    def frame_data(self, file_names: List[str], fds: List[int]) -> bytes:
        data = b''
        for file_name, fd in zip(file_names, fds):
            file_name = os.path.basename(file_name)
            file_name = self.create_header(file_name.encode('utf-8'))
            file_size = os.fstat(fd).st_size
            file_size = self.create_header(str(file_size).encode('utf-8'))
            reader = BufferedFdReader(fd)
            file_data = bytes(file_name + file_size)
            while (bt := reader.readByte()) != None:
                bt = bt.to_bytes(length=1, byteorder='big')
                if bt == self.escape_byte:
                    file_data += self.escape_byte + self.escape_byte
                else:
                    file_data += bt
            data += file_data
        return data

    def unframe_data(self, data: bytes) -> List[Tuple[str, bytes]]:
        headers = []
        payloads = []
        new_data = data.replace(self.escape_byte + self.escape_byte, self.escape_byte)
        while new_data:
            header = new_data[:self.header_size * 2]
            file_name = header[:self.header_size].strip(b'\x00').decode('utf-8')
            file_size = int(header[self.header_size:].strip(b'\x00'))
            payload = new_data[self.header_size * 2: self.header_size * 2 + file_size]
            new_data = new_data[self.header_size * 2 + file_size:]
            headers.append(file_name)
            payloads.append(payload)
        return list(zip(headers, payloads))

# class Tar:
#     DEFAULT_FRAME_SIZE = 1024
#     DEFAULT_HEADER_SIZE = 32
#     def __init__(self, files: List[str], framer: Framer = None):
#         self.files = files
#         self.framer = framer or OutbandFramer(Tar.DEFAULT_FRAME_SIZE, Tar.DEFAULT_HEADER_SIZE, b'\0')

#     def archive(self, output: IO | BinaryIO | TextIO):
#         fds = [os.open(file, os.O_RDONLY) for file in self.files]
#         data = self.framer.frame_data(self.files, fds)
#         output.buffer.write(data)
#         for fd in fds:
#             os.close(fd)
#         output.flush()

#     def extract(self):
#         data = b''
#         for fd in [os.open(file, os.O_RDONLY) for file in self.files]:
#             reader = BufferedFdReader(fd)
#             while (bt := reader.readByte()) is not None:
#                 data += bt.to_bytes(length=1, byteorder='big')
#             reader.close()
#             for file_name, payload in self.framer.unframe_data(data):
#                 fd = os.open(file_name, os.O_WRONLY | os.O_CREAT)
#                 os.write(fd, payload)
#                 os.close(fd)