class HTTPResponder:
    def __init__(self, sock):
        self.sock = sock

    def send_response(self, status_code, status_message, content=b"", content_type="text/plain", headers=None):
        response = f"HTTP/1.1 {status_code} {status_message}\r\n"
        response += f"Content-Type: {content_type}\r\n"
        response += f"Content-Length: {len(content)}\r\n"
        if headers:
            for k, v in headers.items():
                response += f"{k}: {v}\r\n"
        response += "\r\n"
        try:
            self.sock.sendall(response.encode("utf-8") + content)
        finally:
            self.sock.close()

    def send_redirect(self, location="/index.html"):
        headers = {
            "Location": location,
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        }
        self.send_response(302, "Found", b"", "text/plain", headers)
