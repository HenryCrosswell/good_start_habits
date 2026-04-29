# How to deploy to Railway

The app is already deployed on Railway via Docker. This guide covers the initial setup and how to redeploy after changes.

---

## Prerequisites

- [Railway CLI](https://docs.railway.app/develop/cli) installed
- A Railway account
- A project created on Railway (or use an existing one)

---

## Initial deployment

1. Log in:

```bash
railway login
```

2. Link the project:

```bash
railway link
```

3. Set environment variables in the Railway dashboard (or via CLI):

```bash
railway variables set SECRET_KEY=<your key>
railway variables set TRUELAYER_CLIENT_ID=<id>
railway variables set TRUELAYER_CLIENT_SECRET=<secret>
railway variables set TRUELAYER_REDIRECT_URI=https://<your-railway-domain>/auth/callback
railway variables set TRUELAYER_SANDBOX=false
```

4. Deploy:

```bash
railway up
```

Railway builds the Docker image using the `Dockerfile` and runs it with Gunicorn (`--workers 1 --threads 4`).

---

## Persistent database

The SQLite `dashboard.db` is ephemeral on Railway — it will be wiped on each deploy unless you use a Railway Volume.

To add a volume:

1. In the Railway dashboard, go to your service → **Volumes** → **Add Volume**.
2. Set the mount path to `/app`.
3. Railway will mount the volume at `/app`, where `dashboard.db` lives.

After adding the volume, the database persists across deploys and restarts.

---

## Redeploying after code changes

```bash
railway up
```

Or push to your linked Git branch if you have Railway's GitHub integration enabled — Railway redeploys automatically on push.

---

## Checking logs

```bash
railway logs
```

---

## TrueLayer redirect URI

The redirect URI must exactly match what you registered in the TrueLayer console. For Railway:

```
https://<your-service>.up.railway.app/auth/callback
```

Update this in both the TrueLayer console and your Railway environment variables if your domain changes.
