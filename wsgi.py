# wsgi.py
import os
from dotenv import load_dotenv

load_dotenv()

from search import app, load_data

if not load_data():
    raise RuntimeError(
        f"❌ Failed to load JSON‑LD data from {app.config.get('DATA_FILE', 'policies.json')}"
    )

application = app

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
