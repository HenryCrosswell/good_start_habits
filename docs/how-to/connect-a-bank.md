# How to connect a bank account

The budget page pulls transactions from Monzo, Nationwide, and Amex via TrueLayer. You need a TrueLayer account and app credentials to use this.

---

## 1. Get TrueLayer credentials

1. Sign up at [truelayer.com](https://truelayer.com) and create an app.
2. Note your **Client ID** and **Client Secret**.
3. Add `http://localhost:5000/auth/callback` (local) or `https://<your-domain>/auth/callback` (Railway/Pi) as an allowed redirect URI in the TrueLayer console.

---

## 2. Add credentials to `.env`

```
TRUELAYER_CLIENT_ID=<your client id>
TRUELAYER_CLIENT_SECRET=<your client secret>
TRUELAYER_REDIRECT_URI=http://localhost:5000/auth/callback
TRUELAYER_SANDBOX=true
```

Set `TRUELAYER_SANDBOX=true` to use TrueLayer's test environment with fake data. Change to `false` only when you are ready to connect real bank accounts.

---

## 3. Connect a provider

Navigate to `/budget` in the app. Click **Connect** next to Monzo, Nationwide, or Amex.

You will be redirected to TrueLayer, which opens your bank's OAuth login. Authorise access, and TrueLayer redirects back to the app. The access token is stored in SQLite.

---

## 4. Verify the connection

After connecting, the budget page should show real transaction data. If the page shows an error, check the Flask logs — TrueLayer auth failures are logged with the error reason.

---

## Disconnect a provider

On the budget page, click **Disconnect** next to the connected provider. This removes the stored tokens from SQLite.

---

## Token refresh

Access tokens expire after a short period. The app refreshes them automatically:
- On every page load (per-request check before the TrueLayer API call)
- Every hour via a background APScheduler job

You should not need to reconnect unless you revoke access in your bank's app.
