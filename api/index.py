import sys
import os

# Add root directory to sys.path so app, config, and models are discoverable
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Import the production Flask application
from app import app

# Export app instance for Vercel's WSGI runner
app = app

if __name__ == '__main__':
    app.run()
