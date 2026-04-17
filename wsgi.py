# wsgi.py
import os
from dotenv import load_dotenv, find_dotenv

# load .env only when not in production
if os.environ.get("ENV", os.environ.get("FLASK_ENV", "development")) != "production":
    dotenv_path = find_dotenv(usecwd=True)
    if dotenv_path:
        load_dotenv(dotenv_path)

# search.py already calls load_data() at import time,
# so there is no need to call it again here.
from search import app

application = app

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
