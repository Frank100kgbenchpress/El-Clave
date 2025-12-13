import socket
import threading
import ssl


class CustomHTTPServer:
    def __init__(self, host, port, handler_class, deps, ssl_certfile=None, ssl_keyfile=None):
        self.host = host
        self.port = port
        self.handler_class = handler_class
        self.deps = deps
        self.ssl_certfile = ssl_certfile
        self.ssl_keyfile = ssl_keyfile

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)

        # Wrap SSL if certs provided
        if self.ssl_certfile and self.ssl_keyfile:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(certfile=self.ssl_certfile, keyfile=self.ssl_keyfile)
            self.server_socket = context.wrap_socket(self.server_socket, server_side=True)

    def handle_client(self, client_socket, client_address):
        try:
            handler = self.handler_class(client_socket, client_address, self.deps)
            handler.handle()
        except Exception as e:
            print(f"Error atendiendo a {client_address}: {e}")
        finally:
            client_socket.close()

    def serve_forever(self):
        scheme = "https" if (self.ssl_certfile and self.ssl_keyfile) else "http"
        print(f"Servidor corriendo en {scheme}://{self.host}:{self.port}")
        while True:
            client_socket, client_address = self.server_socket.accept()
            thread = threading.Thread(
                target=self.handle_client,
                args=(client_socket, client_address),
                daemon=True,
            )
            thread.start()
