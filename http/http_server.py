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
        # Prepare SSL context (do not wrap the listening socket)
        self.ssl_context = None
        if self.ssl_certfile and self.ssl_keyfile:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.load_cert_chain(certfile=self.ssl_certfile, keyfile=self.ssl_keyfile)
            # Harden minimal settings
            ctx.options |= ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3
            ctx.minimum_version = ssl.TLSVersion.TLSv1_2
            self.ssl_context = ctx

    def handle_client(self, client_socket, client_address):
        try:
            handler = self.handler_class(client_socket, client_address, self.deps)
            handler.handle()
        except Exception as e:
            print(f"Error atendiendo a {client_address}: {e}")
        finally:
            client_socket.close()

    def serve_forever(self):
        scheme = "https" if self.ssl_context else "http"
        print(f"Servidor corriendo en {scheme}://{self.host}:{self.port}")
        while True:
            client_socket, client_address = self.server_socket.accept()
            # Wrap accepted socket if HTTPS enabled
            if self.ssl_context:
                try:
                    client_socket = self.ssl_context.wrap_socket(client_socket, server_side=True)
                except ssl.SSLError as e:
                    print(f"SSL handshake error with {client_address}: {e}")
                    try:
                        client_socket.close()
                    except Exception:
                        pass
                    continue
            thread = threading.Thread(
                target=self.handle_client,
                args=(client_socket, client_address),
                daemon=True,
            )
            thread.start()
