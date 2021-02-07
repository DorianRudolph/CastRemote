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
        print("GET", self.path)
        self._get(False)
        
    def do_HEAD(self):
        print("HEAD", self.path)
        self._get(True)
            

def serve(files, port):
    httpd = HTTPServer(("", port), lambda *args, **kwargs: Handler(files, *args, **kwargs))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    
    
def serve_async(files, port):
    t = Thread(target=serve, args=(files, port))
    t.start()
    return t


#run({"a": (open("mpd-test/test.mpd").read(), "application/dash+xml")})
