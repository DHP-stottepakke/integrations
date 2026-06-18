# integrations for Norwegian DSW KM

A collection of small integration services for the Norwegian DSW knowledge model.
Each integration lives in its own folder under [`services/`](services/) and is
deployed independently.

## Layout

```text
integrations/
├── .github/workflows/deploy.yml   # CD: sync + restart on push to main
├── deploy/
│   ├── policy-search.service      # systemd unit (source of truth)
│   └── DEPLOY.md                  # one-time server setup
└── services/
    └── policy-search/             # the policy search API (Flask + Gunicorn)
        ├── search.py
        ├── wsgi.py
        ├── policies.json
        └── requirements.txt
```

## policy-search

A Flask app that serves a search API over `policies.json`, run with Gunicorn behind
systemd. Endpoints: `/policies/search?q=...`, `/health`, `/config`.

Run locally:

```sh
cd services/policy-search
pip install -r requirements.txt
gunicorn --bind 127.0.0.1:5000 wsgi:application
curl 'http://127.0.0.1:5000/policies/search?q=university'
```

## Deployment (CD)

Pushing a change under `services/policy-search/` to `main` (or running the
**Deploy policy-search** workflow manually) triggers
[`.github/workflows/deploy.yml`](.github/workflows/deploy.yml), which:

1. logs in to the server over SSH with a dedicated key,
2. `rsync`s the service folder to `/opt/integrations/services/policy-search/`, and
3. restarts the systemd service (which runs as `www-data`).

Required GitHub secrets: `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`.

The **one-time server setup** (deploy user, SSH key, sudoers grant, directories,
systemd unit, `.env`) is documented in [deploy/DEPLOY.md](deploy/DEPLOY.md). The
systemd unit itself lives in [deploy/policy-search.service](deploy/policy-search.service).

The `.env` file (production secrets/config) lives only on the server and is never
synced. Dependency changes (`requirements.txt`) are synced but not auto-installed —
re-run `pip install` on the server when they change (see DEPLOY.md).

## Adding a new integration

1. Create `services/<name>/` with its own app, `requirements.txt`, etc.
2. Add a `deploy/<name>.service` systemd unit (copy and adapt `policy-search.service`:
   `WorkingDirectory`, bind address/port, service name).
3. Add a deploy job for it in `.github/workflows/deploy.yml` (copy the existing one;
   adjust the `paths:` filter, rsync source/target, and the `systemctl restart` target).
4. Follow [deploy/DEPLOY.md](deploy/DEPLOY.md) to provision it on the server.
