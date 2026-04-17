# wsgi.py
import os
from dotenv import load_dotenv, find_dotenv

# load .env only when not in production
if os.environ.get("ENV", os.environ.get("FLASK_ENV", "development")) != "production":
    dotenv_path = find_dotenv(usecwd=True)
    if dotenv_path:
        load_dotenv(dotenv_path)

from search import app, load_data


_DATA = None

def load_data_cached():
    global _DATA
    if _DATA is None:
        _DATA = load_data()
    return _DATA



if not load_data():
    raise RuntimeError(
        f"Failed to load JSON‑LD data from {app.config.get('DATA_FILE', 'policies.json')}"
    )

application = app

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
