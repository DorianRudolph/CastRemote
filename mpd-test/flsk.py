from flask.helpers import send_file
import requests
import flask

app = flask.Flask(__name__)


@app.route('/f/<path:path>')
def get_file(path):
    r = send_file(path, conditional=True)
    r.headers['Access-Control-Allow-Origin'] = '*'
    return r


method_requests_mapping = {
    'GET': requests.get,
    'HEAD': requests.head,
    'POST': requests.post,
    'PUT': requests.put,
    'DELETE': requests.delete,
    'PATCH': requests.patch,
    'OPTIONS': requests.options,
}


@app.route('/p/<path:url>', methods=method_requests_mapping.keys())
def proxy(url):
    method = flask.request.method
    if method == "OPTIONS":
        response = flask.make_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "*")
        response.headers.add("Access-Control-Allow-Methods", "*")
        return response
    requests_function = method_requests_mapping[flask.request.method]
    rng = flask.request.headers.get("range")
    headers = {"range": rng} if rng else {}
    request = requests_function(url, stream=True, params=flask.request.args, headers=headers)
    response = flask.Response(flask.stream_with_context(request.iter_content()),
                              content_type=request.headers['content-type'],
                              status=request.status_code)
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
