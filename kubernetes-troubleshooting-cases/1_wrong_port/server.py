import http.server
import socketserver
import sys

Handler = http.server.SimpleHTTPRequestHandler

# Server listens on port 8765
PORT = 8765
print(f"Server started successfully", flush=True)
print(f"Listening on port {PORT}", flush=True)
sys.stdout.flush()

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Ready to accept connections on port {PORT}", flush=True)
    httpd.serve_forever()
