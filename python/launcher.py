from collections import deque
import json
import os
import time
from connection import Resolver, EOF
from environment import get_env

Lock, sleep, spawn, subprocess, Popen = get_env(
    "Lock", "sleep", "spawn", "subprocess", "Popen"
)


class CannotRunError(Exception):
    def __init__(self, message, originalException=None):
        self.originalException = originalException
        super(CannotRunError, self).__init__(message)


# The requests implementation is more complex here if you don't want to send
# a different request per plugin based on when you last got results from it.
class PluginBridge(object):
    def __init__(self, name, metadata_path):
        self._name = name
        self._metadata_dir = os.path.dirname(os.path.abspath(metadata_path))
        with open(metadata_path, "rb") as f:
            self._metadata = json.load(f)
        self._proc = None
        self._resolver = False
        self._requests = deque()
        self._requests_lock = Lock()
        self._request_start_time = None
        self._client_name = None

    def information(self):
        return self._metadata["information"]

    def _start(self):
        if self.running:
            return

        self.stop(True)

        runtime = self._metadata["runtime"]["command"]
        if not isinstance(runtime[0], list):
            runtime = [runtime]
        found = None
        for rt in runtime:
            try:
                self._proc = Popen(
                    rt,
                    cwd=self._metadata_dir,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                )
                self._resolver = Resolver(
                    self, self._proc.stdout, self._proc.stdin
                )
                self._resolver.notify(
                    "helloserver", name=self._name, apiversions=["v0.1"]
                )
                # TODO Should there be a timeout for this ?
                self._resolver.serve(once=True)
                if self._client_name is None:
                    self.stop(True)
                    raise Exception("I/O error")
                found = True
                break
            except Exception as e:
                found = e
        if found is not True:
            self._proc = None
            self._resolver = None
            raise CannotRunError(
                self._metadata["runtime"]["errorMessage"], found
            )

    def serve(self):
        self._start()
        try:
            self._resolver.serve()
        # TODO do you care about knowing about EOF ?
        except EOF:
            self.stop(True)
        except Exception:
            self.stop(True)
            raise

    @property
    def running(self):
        if not self._proc:
            return False
        if self._proc.poll():
            return False
        if self._resolver is None:
            return False
        if self._client_name is None:
            return False
        return True

    # TODO a grace period for shutting down ?
    def stop(self, force=False):
        try:
            if self._resolver:
                self._resolver.notify("shutdown")
        except Exception:
            pass
        if force:
            try:
                self._proc.kill()
            except Exception:
                pass
            self._proc = None
            self._resolver = None
            self._client_name = None
        else:
            if self._proc:
                self._proc.poll()
                if self._proc.returncode:
                    self._proc = None
                    self._resolver = None
                    self._client_name = None
            else:
                self._resolver = None
                self._client_name = None

    def request(self, text):
        with self._requests_lock:
            if not self._requests:
                if self.running:
                    self._request_start_time = time.time()
                    self._resolver.notify("request", text)
                    return
            self._requests.append({"text": text})
            return

    def _process_pending_requests(self):
        if self._requests:
            with self._requests_lock:
                last = None
                while self._requests:
                    last = self._requests.popleft()
                    if self._requests:
                        self._request_start_time = time.time()
                        self.on_entriesfinished(fake=True)
                if last:
                    self._request_start_time = time.time()
                    self._resolver.notify(
                        "request", last["text"]
                    )

    def on_helloclient(self, name, apiversion):
        self._client_name = name
        self._process_pending_requests()

    def on_entriesadd(self, entries):
        print("add", entries)

    def on_entriesfinished(self, fake=False):
        request_time = time.time() - self._request_start_time
        print("finished", request_time, fake)
        if not fake:
            self._process_pending_requests()

    def on_entriesremove(self, ids):
        print("remove", ids)

    def on_entriesremoveall(self):
        print("removeall")

    def on_error(self, method, msg):
        print("error", method, msg)


pluginBridge = PluginBridge("Test launcher v0.1", "metadata.json")
pluginBridge.request("(1 - (-2)) * 3.2")
thread = spawn(pluginBridge.serve)
sleep(2)
for i in range(10):
    pluginBridge.request("(1 - (-2)) * 3.2 + %d" % i)
    sleep(0.1)
pluginBridge.stop()
thread.join()

thread = spawn(pluginBridge.serve)
sleep(2)
for i in range(10):
    pluginBridge.request("(1 - (-2)) * 3.2 + %d" % i)
    sleep(0.1)
pluginBridge.stop()
thread.join()
