import usocket as socket
import ubinascii as binascii
import urandom as random
import uselect as select
import ustruct as struct
from message import *

_OP_TEXT = 0x1
_OP_BYTES = 0x2
_OP_CLOSE = 0x8
_OP_PING = 0x9
_OP_PONG = 0xa


class WSClient:
    
    def __init__(self, uri, on_message=None, on_connect=None, on_close=None):
        self.uri = uri
        self.on_message = on_message
        self.on_connect = on_connect
        self.on_close = on_close
        self.open = False
        self._sock = None
        self._stream = None
        self._poll = None
        self._connect()

    def _parse_uri(self, uri):
        if uri.startswith("ws://"):
            uri = uri[5:]
        elif uri.startswith("wss://"):
            raise ValueError("wss:// non supporté")
        
        path = "/"
        if "/" in uri:
            idx = uri.index("/")
            path = uri[idx:]
            uri = uri[:idx]
        
        if ":" in uri:
            host, port = uri.split(":")
            port = int(port)
        else:
            host, port = uri, 80
        
        return host, port, path

    def _connect(self):
        host, port, path = self._parse_uri(self.uri)
        
        addr = socket.getaddrinfo(host, port)[0][-1]
        self._sock = socket.socket()
        self._sock.settimeout(10)
        self._sock.connect(addr)
        
        self._stream = self._sock.makefile("rwb", 0)
        
        key = binascii.b2a_base64(bytes(random.getrandbits(8) for _ in range(16)))[:-1]
        
        self._stream.write(b"GET %s HTTP/1.1\r\n" % path.encode())
        self._stream.write(b"Host: %s:%d\r\n" % (host.encode(), port))
        self._stream.write(b"Connection: Upgrade\r\n")
        self._stream.write(b"Upgrade: websocket\r\n")
        self._stream.write(b"Sec-WebSocket-Key: %s\r\n" % key)
        self._stream.write(b"Sec-WebSocket-Version: 13\r\n")
        self._stream.write(b"\r\n")
        
        status = self._stream.readline()
        if not status.startswith(b"HTTP/1.1 101"):
            self._sock.close()
            raise OSError("Handshake failed: %s" % status)
        
        while True:
            line = self._stream.readline()
            if not line or line == b"\r\n":
                break
        
        self._sock.setblocking(False)
        self._poll = select.poll()
        self._poll.register(self._sock, select.POLLIN)
        self.open = True
        if self.on_connect:
            self.on_connect(self)


    def poll(self):
        if not self.open:
            return None
        
        events = self._poll.poll(0)
        if not events:
            return None
        
        try:
            return self._read_message()
        except OSError:
            self._close()
            return None

    def _read_message(self):
        header = self._stream.read(2)
        if not header or len(header) < 2:
            return None
        
        byte1, byte2 = struct.unpack('!BB', header)
        opcode = byte1 & 0x0f
        length = byte2 & 0x7f
        
        if length == 126:
            length, = struct.unpack('!H', self._stream.read(2))
        elif length == 127:
            length, = struct.unpack('!Q', self._stream.read(8))
        
        if byte2 & 0x80:
            mask = self._stream.read(4)
            data = self._stream.read(length)
            data = bytes(b ^ mask[i & 3] for i, b in enumerate(data))
        else:
            data = self._stream.read(length) if length else b""
        
        if opcode == _OP_TEXT:
            msg = data.decode('utf-8')
            if self.on_message:
                self.on_message(msg)

            return msg
        elif opcode == _OP_BYTES:
            if self.on_message:
                self.on_message(data)
            return data
        elif opcode == _OP_CLOSE:
            self._close()
            return None
        elif opcode == _OP_PING:
            self._write_frame(_OP_PONG, data)
            return self.poll()
        elif opcode == _OP_PONG:
            return self.poll()
        
        return None

    def _write_frame(self, opcode, data=b''):
        if isinstance(data, str):
            data = data.encode('utf-8')
        length = len(data)
        
        byte1 = 0x80 | opcode
        byte2 = 0x80
        
        if length < 126:
            byte2 |= length
            self._stream.write(struct.pack('!BB', byte1, byte2))
        elif length < 65536:
            byte2 |= 126
            self._stream.write(struct.pack('!BBH', byte1, byte2, length))
        else:
            byte2 |= 127
            self._stream.write(struct.pack('!BBQ', byte1, byte2, length))
        
        mask = struct.pack('!I', random.getrandbits(32))
        self._stream.write(mask)
        
        if data:
            self._stream.write(bytes(b ^ mask[i & 3] for i, b in enumerate(data)))

    def send(self, data):
        if not self.open:
            return
        if isinstance(data, str):
            self._write_frame(_OP_TEXT, data)
        else:
            self._write_frame(_OP_BYTES, data)

    def close(self):
        if self.open:
            try:
                self._write_frame(_OP_CLOSE, struct.pack('!H', 1000))
            except:
                pass
            self._close()

    def _close(self):
        self.open = False
        try:
            self._poll.unregister(self._sock)
        except:
            pass
        try:
            self._sock.close()
        except:
            pass
        if self.on_close:
            self.on_close()




