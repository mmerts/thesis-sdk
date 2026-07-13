from flask import Flask
import os
import sys

app = Flask(__name__)

# Application requires these environment variables
REQUIRED_ENV_VARS = ['APP_MODE', 'DATABASE_URL', 'API_KEY']

def check_environment():
    """Check if all required environment variables are set"""
    missing = []
    for var in REQUIRED_ENV_VARS:
        if var not in os.environ:
            missing.append(var)
    return missing

# Check on startup
missing_vars = check_environment()
if missing_vars:
    error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
    print(f"ERROR: {error_msg}", file=sys.stderr)
    # Application will crash immediately
    raise EnvironmentError(error_msg)

@app.route('/')
def hello():
    app_mode = os.environ.get('APP_MODE', 'unknown')
    db_url = os.environ.get('DATABASE_URL', 'not-set')
    return f"App running in {app_mode} mode with database: {db_url}"

@app.route('/health')
def health():
    # Re-check environment variables
    missing = check_environment()
    if missing:
        return f"Missing env vars: {missing}", 503
    return "OK", 200

if __name__ == '__main__':
    print(f"Starting in {os.environ.get('APP_MODE')} mode")
    app.run(host='0.0.0.0', port=8080)
