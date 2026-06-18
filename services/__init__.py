# Application factory — mounts each integration as a Flask Blueprint.
import os
from flask import Flask, jsonify


def _load_dotenv_if_dev() -> None:
    """Load a .env in development only; in production systemd provides the env."""
    if os.environ.get("ENV", os.environ.get("FLASK_ENV", "development")) == "production":
        return
    try:
        from dotenv import load_dotenv, find_dotenv
        path = find_dotenv(usecwd=True)
        if path:
            load_dotenv(path)
    except Exception:
        pass


def create_app() -> Flask:
    _load_dotenv_if_dev()

    app = Flask(__name__)

    # Importing a blueprint module loads its data at import time (Gunicorn --preload).
    from .policy_search import bp as policy_search_bp, loaded as policies_loaded
    from .relation_type import bp as relation_type_bp, loaded as relationtype_loaded

    app.register_blueprint(policy_search_bp)
    app.register_blueprint(relation_type_bp)

    @app.route('/health', methods=['GET'])
    def health():
        ok = policies_loaded() and relationtype_loaded()
        return jsonify({
            'status': 'ok' if ok else 'degraded',
            'policies_loaded': policies_loaded(),
            'relationtype_loaded': relationtype_loaded(),
        }), (200 if ok else 503)

    return app
