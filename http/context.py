class HTTPContext:
    def __init__(self, method, path, headers, body):
        self.method = method
        self.path = path
        self.headers = headers
        self.body = body

    @staticmethod
    def parse(sock):
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = sock.recv(1024)
            if not chunk:
                break
            data += chunk
        if b"\r\n\r\n" not in data:
            return None
        header_end = data.find(b"\r\n\r\n")
        headers_raw = data[:header_end].decode("utf-8", errors="replace")
        body = data[header_end + 4:]
        lines = headers_raw.split("\r\n")
        if not lines:
            return None
        try:
            request_line = lines[0]
            method, path, _ = request_line.split()
        except Exception:
            return None
        headers = {}
        for line in lines[1:]:
            if not line:
                continue
            if ": " in line:
                k, v = line.split(": ", 1)
                headers[k] = v
        content_length = int(headers.get("Content-Length", 0))
        remaining = content_length - len(body)
        while remaining > 0:
            chunk = sock.recv(remaining)
            if not chunk:
                break
            body += chunk
            remaining -= len(chunk)
        return HTTPContext(method, path, headers, body)
