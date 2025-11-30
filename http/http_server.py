import socket


class CustomHTTPServer:
    def __init__(self, host, port, handler_class, deps):
        self.host = host
        self.port = port
        self.handler_class = handler_class
        self.deps = deps
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)

    def serve_forever(self):
        print(f"Servidor corriendo en http://{self.host}:{self.port}")
        while True:
            client_socket, client_address = self.server_socket.accept()
            handler = self.handler_class(client_socket, client_address, self.deps)
            handler.handle()
