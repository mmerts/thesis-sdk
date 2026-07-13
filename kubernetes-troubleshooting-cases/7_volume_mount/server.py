from flask import Flask
import os

app = Flask(__name__)

CONFIG_FILE = '/etc/config/app.conf'

@app.route('/')
def hello():
    try:
        # Try to read configuration file
        with open(CONFIG_FILE, 'r') as f:
            config = f.read()
        return f"App running with config: {config}"
    except FileNotFoundError:
        return f"ERROR: Config file not found at {CONFIG_FILE}", 500
    except Exception as e:
        return f"ERROR: {str(e)}", 500

@app.route('/health')
def health():
    # Health check fails if config is missing
    if os.path.exists(CONFIG_FILE):
        return "OK", 200
    return "Config file missing", 503

if __name__ == '__main__':
    print(f"Starting app, looking for config at {CONFIG_FILE}")
    app.run(host='0.0.0.0', port=8080)
