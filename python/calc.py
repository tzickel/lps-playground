import re
import sys
from connection import BasePlugin, from_stdio


class CalculatorPlugin(BasePlugin):
    def __init__(self, name, read, write):
        self._match = re.compile(r"^[0-9+\-*/ .()]+$")
        self._server_name = None
        self._running_id = 0
        super(CalculatorPlugin, self).__init__(name, read, write)

    def on_helloserver(self, name, apiversions):
        self._server_name = name
        self.notify("helloclient", name=self._name, apiversion="v0.1")

    def on_request(self, id, text):
        self.notify("entriesremoveall")
        try:
            if text and self._match.match(text):
                result = eval(text)
                self._running_id += 1
                self.notify(
                    "entriesadd",
                    [{"id": str(self._running_id), "text": result}],
                )
        except Exception:
            pass
        finally:
            self.notify("entriesfinished", id=id)

    def on_shutdown(self):
        sys.exit(0)


if __name__ == "__main__":
    CalculatorPlugin("Simple Calculator v0.1", **from_stdio()).serve()
