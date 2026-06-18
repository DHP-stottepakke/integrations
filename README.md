# integrations for Norwegian DSW KM

A collection of small integrations for the Norwegian DSW knowledge model. They are
served by a **single Flask app** (one Gunicorn/systemd service on port 80); each
integration is a Flask **Blueprint** mounted under its own path.

## Layout

```text
integrations/
├── wsgi.py                         # Gunicorn entrypoint: create_app()
├── requirements.txt                # runtime deps (Flask, gunicorn, python-dotenv)
├── .github/workflows/
│   ├── deploy.yml                  # CD: sync app + restart service on push to main
│   └── relation-type.yml           # weekly: rebuild DataCite vocab, commit, deploy
├── deploy/
│   ├── integrations.service        # systemd unit (source of truth)
│   └── DEPLOY.md                   # one-time server setup
└── services/                       # the app package
    ├── __init__.py                 # create_app(): registers blueprints + /health
    ├── policy_search/              # policy search over policies.json
    │   ├── __init__.py
    │   └── policies.json
    └── relation_type/              # DataCite relationType vocabulary
        ├── __init__.py
        ├── build.py                # builds the combined JSON-LD from upstream
        ├── relationType.jsonld     # combined doc (auto-synced from DataCite)
        ├── LICENSE                 # Apache-2.0 (DataCite-derived content)
        └── NOTICE
```

## Endpoints

| Path                                | Description                                   |
| ----------------------------------- | --------------------------------------------- |
| `/policies/search?q=...`            | Search policies (`name`, `alternateName`, …). |
| `/policies/config`                  | Effective policy-search config.               |
| `/datacite/relationtype`            | Full combined DataCite relationType JSON-LD.  |
| `/datacite/relationtype/search?q=`  | Search relationType `prefLabel` + `definition`. |
| `/health`                           | Liveness + per-integration data-loaded flags. |

Run locally:

```sh
pip install -r requirements.txt
gunicorn --bind 127.0.0.1:5000 wsgi:application
curl 'http://127.0.0.1:5000/policies/search?q=university'
curl 'http://127.0.0.1:5000/datacite/relationtype/search?q=cites'
```

## DataCite relationType sync

`services/relation_type/build.py` fetches the upstream vocabulary folder
([datacite/schema.datacite.org-linked-data → vocab/relationType](https://github.com/datacite/schema.datacite.org-linked-data/tree/main/vocab/relationType))
and combines the individual SKOS concept files + `context.jsonld` + the `ConceptScheme`
into one self-contained JSON-LD document (`relationType.jsonld`).

GitHub Actions cannot watch another repo with a `paths:` filter, so
[`.github/workflows/relation-type.yml`](.github/workflows/relation-type.yml) runs **weekly**
(and on demand): it rebuilds the file, commits only if it changed, and then deploys.

## Deployment (CD)

Pushing app changes to `main` (or running **Deploy** manually) triggers
[`.github/workflows/deploy.yml`](.github/workflows/deploy.yml), which logs in over SSH with a
dedicated key, `rsync`s the app to `/opt/integrations/`, and restarts the single
`integrations` systemd service (which runs as `www-data`).

Required GitHub secrets: `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`. The **one-time server
setup** (deploy user, SSH key, sudoers grant, directory, systemd unit, `.env`) is documented in
[deploy/DEPLOY.md](deploy/DEPLOY.md); the unit is [deploy/integrations.service](deploy/integrations.service).

The `.env` (production secrets/config) lives only on the server and is never synced. Dependency
changes (`requirements.txt`) are synced but not auto-installed — re-run `pip install` on the
server when they change (see DEPLOY.md).

## Licensing

This repository's own content is dedicated to the public domain under **CC0 1.0** (see
[LICENSE](LICENSE)). The exception is `services/relation_type/`, whose data derives from the
DataCite `schema.datacite.org-linked-data` project and is licensed under the **Apache License
2.0** — see [services/relation_type/LICENSE](services/relation_type/LICENSE) and
[services/relation_type/NOTICE](services/relation_type/NOTICE). The combined
`relationType.jsonld` carries an `SPDX-License-Identifier: Apache-2.0` field.

## Adding a new integration

1. Create `services/<name>/__init__.py` exposing a Flask `bp = Blueprint(...)` (and a
   `loaded()` helper if it loads data).
2. Register it in [services/__init__.py](services/__init__.py) (`create_app()`).
3. Add its dependencies to the root `requirements.txt` if any.

No new systemd unit or deploy workflow is needed — the single service and `deploy.yml`
already cover the whole `services/` package.
