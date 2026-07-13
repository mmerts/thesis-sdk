from flask import Flask
import time

app = Flask(__name__)

start_time = time.time()

@app.route('/')
def hello():
    return "Application is running!"

@app.route('/ready')
def ready():
    # Application is ready after 5 seconds
    if time.time() - start_time > 5:
        return "Ready", 200
    return "Not ready yet", 503

# Note: No /health endpoint defined!
# Liveness probe will fail

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
