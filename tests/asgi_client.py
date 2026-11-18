import json
import urllib.parse
from io import BytesIO
from typing import Dict, Any, Optional


class MockResponse:
    def __init__(self, status_code: int, headers: Dict[str, str], body: bytes):
        self.status_code = status_code
        self.headers = headers
        self._body = body

    @property
    def content(self) -> bytes:
        return self._body

    @property
    def text(self) -> str:
        return self._body.decode("utf-8")

    def json(self) -> Any:
        return json.loads(self.text)


class DirectTestClient:
    """Pure in-memory ASGI test client that directly invokes app(scope, receive, send)
    without sockets, threads, or background portals.
    """
    def __init__(self, app):
        self.app = app
        self.cookies: Dict[str, str] = {}

    def _sync_call(self, coro):
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    def request(
        self,
        method: str,
        path: str,
        json: Optional[Any] = None,
        data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        client_host: str = "127.0.0.1"
    ) -> MockResponse:
        parsed_url = urllib.parse.urlparse(path)
        raw_path = parsed_url.path
        query_string = parsed_url.query.encode("ascii")

        body_bytes = b""
        req_headers = dict(headers or {})

        if json is not None:
            import json as _json
            body_bytes = _json.dumps(json).encode("utf-8")
            req_headers["content-type"] = "application/json"
        elif data is not None:
            if isinstance(data, dict):
                body_bytes = urllib.parse.urlencode(data).encode("utf-8")
                req_headers["content-type"] = "application/x-www-form-urlencoded"
            elif isinstance(data, (bytes, bytearray)):
                body_bytes = bytes(data)
            elif isinstance(data, str):
                body_bytes = data.encode("utf-8")

        req_headers["content-length"] = str(len(body_bytes))

        # Merge cookies
        merged_cookies = dict(self.cookies)
        if cookies:
            merged_cookies.update(cookies)
        if merged_cookies:
            req_headers["cookie"] = "; ".join(f"{k}={v}" for k, v in merged_cookies.items())

        asgi_headers = [
            (k.lower().encode("latin1"), v.encode("latin1"))
            for k, v in req_headers.items()
        ]

        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": method.upper(),
            "scheme": "http",
            "path": raw_path,
            "raw_path": raw_path.encode("ascii"),
            "query_string": query_string,
            "root_path": "",
            "headers": asgi_headers,
            "client": (client_host, 12345),
            "server": ("testserver", 80),
        }

        request_body_sent = False

        async def receive():
            nonlocal request_body_sent
            if not request_body_sent:
                request_body_sent = True
                return {"type": "http.request", "body": body_bytes, "more_body": False}
            return {"type": "http.request", "body": b"", "more_body": False}

        status_code = 200
        response_headers = {}
        response_body = BytesIO()

        async def send(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                for k, v in message.get("headers", []):
                    key = k.decode("latin1").lower()
                    val = v.decode("latin1")
                    if key == "set-cookie":
                        # Parse cookie
                        cookie_part = val.split(";")[0]
                        if "=" in cookie_part:
                            ck_name, ck_val = cookie_part.split("=", 1)
                            self.cookies[ck_name.strip()] = ck_val.strip()
                    response_headers[key] = val
            elif message["type"] == "http.response.body":
                response_body.write(message.get("body", b""))

        async def run_asgi():
            await self.app(scope, receive, send)

        self._sync_call(run_asgi())

        return MockResponse(
            status_code=status_code,
            headers=response_headers,
            body=response_body.getvalue()
        )

    def get(self, path: str, **kwargs) -> MockResponse:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> MockResponse:
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs) -> MockResponse:
        return self.request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs) -> MockResponse:
        return self.request("DELETE", path, **kwargs)
