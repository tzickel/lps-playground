from collections import OrderedDict
import json
import sys
from environment import get_env

Lock = get_env("Lock")


class EOF(Exception):
    pass


class InvalidInput(Exception):
    pass


# TODO error handling


class Connection(object):
    def __init__(self, read, write):
        self._read = read
        self._write = write
        self._write_lock = Lock()

    def serve(self, once=False):
        state = 0
        while not self._read.closed:
            if state == 0:
                headers = {}
                state = 1
            if state == 1:
                line = self._read.readline()
                if line == b"":
                    raise EOF()
                elif line == b"\r\n":
                    state = 2
                else:
                    key, value = line.split(b":", 1)
                    key = key.strip().lower()
                    value = value.strip()
                    headers[key] = value
            if state == 2:
                length = int(headers[b"content-length"])
                body = self._read.read(length)
                state = 0
                body = json.loads(body.decode("utf-8"))
                self._message(body)
                if once:
                    break

    def close(self):
        try:
            self._read.close()
        finally:
            with self._write_lock:
                self._write.close()

    def notify(self, method, *args, **kwargs):
        if args and kwargs:
            raise InvalidInput()
        if args:
            params = args
        elif kwargs:
            params = kwargs
        else:
            params = []
        body = OrderedDict(
            [("jsonrpc", "2.0"), ("method", method), ("params", params)]
        )
        body = json.dumps(body).encode("utf-8")
        header = b"Content-Length: %d\r\n\r\n" % len(body)
        with self._write_lock:
            self._write.write(header)
            self._write.write(body)
            self._write.flush()

    def _message(self, body):
        pass


class Resolver(Connection):
    def __init__(self, obj, read, write):
        self._obj = obj
        super(Resolver, self).__init__(read, write)

    def _message(self, msg):
        method_name = "on_" + msg["method"]
        method = getattr(self._obj, method_name, None)
        if method:
            # TODO return error on type error or just bork ?
            # TODO what to do on general exceptions from calling method ?
            if isinstance(msg["params"], list) and msg["params"]:
                method(*msg["params"])
            else:
                method(**(msg["params"] or {}))
        else:
            self.notify("error", msg["method"], "method not found")


class BasePlugin(object):
    def __init__(self, name, read, write):
        self._name = name
        self._resolver = Resolver(self, read, write)

    def serve(self, once=False):
        self._resolver.serve(once)

    def notify(self, method, *args, **kwargs):
        self._resolver.notify(method, *args, **kwargs)


def from_stdio():
    return {
        "read": getattr(sys.stdin, "buffer", sys.stdin),
        "write": getattr(sys.stdout, "buffer", sys.stdout),
    }
