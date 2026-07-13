from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return "Hello from Wrong Interface App!"

@app.route('/health')
def health():
    return "OK", 200

if __name__ == '__main__':
    # WRONG: Binding to localhost only!
    # This makes the app unreachable from outside the container
    app.run(host='127.0.0.1', port=8080)

    # CORRECT would be:
    # app.run(host='0.0.0.0', port=8080)
