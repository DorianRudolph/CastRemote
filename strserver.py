# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# at your option) any later version.

from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread


class Handler(BaseHTTPRequestHandler):
    def __init__(self, files, *args, **kwargs):
        self._files = files
        super().__init__(*args, **kwargs)
        
    def _get(self, head):
        if file := self._files.get(self.path[1:]):
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-type', file[1])
            self.end_headers()
            if not head:
                self.wfile.write(file[0].encode())
        else:
            self.send_response(404)
        
    def do_GET(self):
        # print("GET", self.path)
        self._get(False)
        
    def do_HEAD(self):
        # print("HEAD", self.path)
        self._get(True)

    
def serve(files, port):
    def forever():
        httpd.serve_forever(poll_interval=0.1)
        httpd.server_close()
    httpd = HTTPServer(("", port), lambda *args, **kwargs: Handler(files, *args, **kwargs))
    t = Thread(target=forever)
    t.start()
    return t, httpd
