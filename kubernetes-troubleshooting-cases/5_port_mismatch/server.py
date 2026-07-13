from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return "Hello from Port Mismatch App!"

@app.route('/health')
def health():
    return "OK", 200

if __name__ == '__main__':
    # Application runs on port 5000
    app.run(host='0.0.0.0', port=5000)
