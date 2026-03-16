# integrations for Norwegian DSW KM

deploy with e.g. Gunicorn and systemd

````systemd
[Unit]
Description=Gunicorn instance serving the policy search API
After=network.target

[Service]
# ---- USER / GROUP -------------------------------------------------
# Run as a non‑root user for safety.  www-data is common on Debian/Ubuntu,
# but you can create a dedicated user e.g. `search`.
User=www-data
Group=www-data

# ---- WORKING DIRECTORY --------------------------------------------
WorkingDirectory=/var/www-data/integrations

# ---- VIRTUAL ENVIRONMENT -------------------------------------------
ExecStart=/usr/bin/gunicorn \
          --bind [IP] \
          wsgi:app
CapabilityBoundingSet=CAP_NET_BIND_SERVICE
AmbientCapabilities=CAP_NET_BIND_SERVICE

# ---- ENVIRONMENT ----------------------------------------------------
# Load .env file (optional, useful if you keep secrets there)
EnvironmentFile=/var/www-data/integrations/.env

# ---- RESTART POLICY ------------------------------------------------
Restart=on-failure
RestartSec=5

# ---- LOGGING -------------------------------------------------------
# Journal will capture stdout / stderr.
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target

````

````sh
# .env
FLASK_ENV=production
FLASK_DEBUG=False
DATA_FILE=
HOST=
PORT=
WORKERS=
````

