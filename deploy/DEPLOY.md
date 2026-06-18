# Deployment

One Gunicorn service (`integrations`) serves every integration on port 80, mounted by path:
`/policies/...`, `/datacite/relationtype/...`, and `/health`.

The [CD workflow](../.github/workflows/deploy.yml) rsyncs the whole app to `/opt/integrations`
and restarts the service whenever code/data changes on `main` (or when run manually). It logs in
over SSH with a dedicated key. The [weekly sync workflow](../.github/workflows/relation-type.yml)
rebuilds the DataCite vocabulary and triggers the same deploy when it changes.

This is a **one-time server setup** guide. Once it's done, deploys are automatic.

## 1. GitHub repository secrets

Settings → Secrets and variables → Actions → *New repository secret*:

| Secret           | Value                                  |
| ---------------- | -------------------------------------- |
| `DEPLOY_HOST`    | `158.39.201.47`                        |
| `DEPLOY_USER`    | `deploy`                               |
| `DEPLOY_SSH_KEY` | the **private** key (full file, incl. header/footer lines) |

(`GITHUB_TOKEN` is provided automatically to the sync workflow — no setup needed.)

## 2. Dedicated deploy SSH key

Generate a key pair *for CI only* (no passphrase, since CI is non-interactive):

```sh
ssh-keygen -t ed25519 -f deploy_key -C "github-actions-deploy" -N ""
```

- Put the contents of `deploy_key` (private) into the `DEPLOY_SSH_KEY` secret.
- Append `deploy_key.pub` to the deploy user's `~/.ssh/authorized_keys` on the server (step 3).
- Delete the local copies afterwards.

## 3. Deploy user + directory (run on the server, as root/sudo)

```sh
# Dedicated unprivileged user that owns the code and runs the deploy.
sudo adduser --disabled-password --gecos "" deploy

# Authorize the CI public key.
sudo install -d -m 700 -o deploy -g deploy /home/deploy/.ssh
echo "<contents of deploy_key.pub>" | sudo tee -a /home/deploy/.ssh/authorized_keys
sudo chown deploy:deploy /home/deploy/.ssh/authorized_keys
sudo chmod 600 /home/deploy/.ssh/authorized_keys

# Target directory, owned by the deploy user so rsync can write.
sudo mkdir -p /opt/integrations
sudo chown -R deploy:deploy /opt/integrations
```

Synced files keep their default modes (files `644`, dirs `755`), so the `www-data`
service user can read and execute them. Secrets are **not** synced — see step 6.

## 4. Passwordless restart (narrow sudoers grant)

The deploy user must restart the service without a password, but nothing more.

```sh
# Confirm the systemctl path first; some distros use /bin/systemctl.
command -v systemctl

# Create the drop-in (must be mode 0440). Adjust the path if needed.
echo 'deploy ALL=(root) NOPASSWD: /usr/bin/systemctl restart integrations' \
  | sudo tee /etc/sudoers.d/deploy
sudo chmod 440 /etc/sudoers.d/deploy
sudo visudo -c   # validate syntax
```

## 5. Python dependencies (one-time, and after any requirements change)

The CD pipeline syncs `requirements.txt` but does **not** install it (deploys stay
lean and don't need broad sudo). Install dependencies once:

```sh
sudo pip install -r /opt/integrations/requirements.txt
# or install gunicorn + Flask via your package manager to match /usr/bin/gunicorn
```

Re-run this manually whenever `requirements.txt` changes.

## 6. Environment file (server-only secrets)

```sh
sudo -u deploy tee /opt/integrations/.env >/dev/null <<'EOF'
FLASK_ENV=production
FLASK_DEBUG=False
EOF
sudo chmod 640 /opt/integrations/.env
```

`.env` is excluded from rsync, so deploys never overwrite or delete it. The systemd unit
already sets `ENV=production`, so `.env` is optional.

## 7. Install and start the service

```sh
# Copy the unit from a checkout of the repo:
sudo cp deploy/integrations.service /etc/systemd/system/integrations.service
sudo systemctl daemon-reload
sudo systemctl enable --now integrations
systemctl status integrations
```

## 8. Verify

```sh
curl http://158.39.201.47/health                          # {"status":"ok","policies_loaded":true,...}
curl 'http://158.39.201.47/policies/search?q=university'
curl 'http://158.39.201.47/datacite/relationtype/search?q=cites'
journalctl -u integrations -f                             # live logs
```

After this, pushing app changes to `main` (or the weekly sync committing a vocabulary
update) will rsync the app and restart the service automatically.
