#!/usr/bin/env python3
"""Simple HTTP server for misspelling test case."""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        response = {"status": "ok", "app": "misspelling-app", "version": "latest"}
        self.wfile.write(json.dumps(response).encode())

    def log_message(self, format, *args):
        print(f"[misspelling-app] {args[0]}")

if __name__ == "__main__":
    server = HTTPServer(('0.0.0.0', 8080), Handler)
    print("misspelling-app:latest running on port 8080")
    server.serve_forever()
