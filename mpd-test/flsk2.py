from flask import Flask
from flask.helpers import send_file
from flask_cors import CORS


app = Flask(__name__)
CORS(app)


@app.route('/f/<path:path>')
def get_big_file(path):
    r = send_file(path, conditional=True)
    return r


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
