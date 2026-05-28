# Microsoft Entra ID — operator setup

The Agent Genesis API authenticates users with Microsoft Entra ID (Azure AD) and talks to Microsoft Graph on the user's behalf via the **On-Behalf-Of (OBO)** flow. This doc takes you from a fresh Entra tenant to a `.env` ready to boot.

Estimated time: **15–20 minutes**. Requires tenant admin to grant consent for two Graph permissions.

## Prerequisites

- Tenant admin or "Cloud Application Administrator" role.
- The frontend dev URL: `http://localhost:5173` (or your prod equivalent).

---

## 1. Create the app registration

Azure portal → **Microsoft Entra ID** → **App registrations** → **New registration**.

| Field | Value |
|---|---|
| Name | `Agent Genesis` (or anything) |
| Supported account types | **Single tenant** (recommended for v1) |
| Redirect URI platform | **Single-page application (SPA)** |
| Redirect URI | `http://localhost:5173` |

Register. Copy these from the **Overview** blade:
- **Directory (tenant) ID** → `AG_ENTRA_TENANT_ID`
- **Application (client) ID** → `AG_ENTRA_CLIENT_ID`

---

## 2. Expose the API

App registration → **Expose an API**.

1. **Application ID URI**: set to `api://agentgenesis-api` (click "Add" or "Set").
2. **Add a scope**:
   - Scope name: `access_as_user`
   - Who can consent: **Admins and users**
   - Admin consent display name: `Access Agent Genesis on your behalf`
   - Admin consent description: same
   - State: **Enabled**

3. **Authorized client applications** → **Add a client application**:
   - Client ID: paste this app's own `client_id` (the GUID from step 1).
   - Authorized scopes: check `api://agentgenesis-api/access_as_user`.
   - Add. This skips the combined-consent prompt for end users when MSAL.js requests the scope.

---

## 3. Enable the confidential-client side (web platform) for OBO

App registration → **Authentication** → **Add a platform** → **Web**.

| Field | Value |
|---|---|
| Redirect URI | (leave blank — backend doesn't redirect) |
| Front-channel logout URL | (leave blank) |
| Implicit/hybrid grants | leave both **unchecked** |

Save. You now have both `spa` and `web` platforms configured on the same app registration. This is required because OBO is a confidential-client flow and the SPA flow is a public-client flow.

Then **Certificates & secrets** → **New client secret** → 24 months (or shorter). Copy the **Value** (only shown once) → `AG_ENTRA_CLIENT_SECRET`.

---

## 4. Add Graph API permissions (delegated)

App registration → **API permissions** → **Add a permission** → **Microsoft Graph** → **Delegated permissions**.

Add exactly these three:

| Permission | What it does |
|---|---|
| `User.Read` | Sign-in identity. |
| `OnlineMeetingRecording.Read.All` | Read meeting recordings. |
| `OnlineMeetingTranscript.Read.All` | Read meeting transcripts. |

Two of those require **admin consent**. Click **Grant admin consent for `<tenant>`** at the top of the table. Confirm.

If you can't grant consent yourself, send this URL to the tenant admin (replace `{tenant}` and `{client_id}`):

```
https://login.microsoftonline.com/{tenant}/adminconsent?client_id={client_id}
```

> **Important constraint — delegated content download is organizer-only.**
> Per Microsoft Graph, downloading recording or transcript content via delegated permissions is **only allowed for the meeting organizer**. Users who only *attended* a meeting will get 403 when they try to read its recording. v1 ships with this constraint documented; coverage for attendees needs app-only client credentials (a future plan).

---

## 5. Edit the app manifest

App registration → **Manifest**.

You're going to edit three JSON properties. Find each and change the value, then **Save**.

**5.1 — Emit v2 access tokens.** Find:

```json
"accessTokenAcceptedVersion": null
```

Change to:

```json
"accessTokenAcceptedVersion": 2
```

This makes the token's `aud` claim the client-id GUID (which is what the backend validates). Leaving it `null` emits v1 tokens whose `aud` is the App ID URI — the backend would reject them.

**5.2 — Include `oid` as an optional access-token claim.** Find:

```json
"optionalClaims": null
```

Replace with:

```json
"optionalClaims": {
  "accessToken": [
    { "name": "oid" },
    { "name": "tid" }
  ]
}
```

`oid` is the stable per-user identifier. v2 access tokens don't include it by default; the backend requires it.

**5.3 — Set `knownClientApplications`** to enable combined consent across the SPA + Graph scopes:

```json
"knownClientApplications": ["<this app's client_id>"]
```

(Yes, the same GUID as the app itself. This intentional self-reference is what tells Entra "these two clients are the same product so consent prompts can combine".)

**Save**.

---

## 6. Wire it into `api/.env`

```bash
cp api/.env.example api/.env
```

Then fill in:

```
AG_ENVIRONMENT=dev
AG_ENTRA_TENANT_ID=<tenant guid from step 1>
AG_ENTRA_CLIENT_ID=<client guid from step 1>
AG_ENTRA_CLIENT_SECRET=<value from step 3>
AG_ANTHROPIC_API_KEY=<your Anthropic key>
```

---

## 7. Smoke-test

```bash
cd api
uv run uvicorn agentgenesis_api.main:create_app --factory --port 8000
```

Boot must succeed. If you see `ValidationError: AG_ENTRA_TENANT_ID is missing`, recheck step 6.

Once Phase 6 lands, hit `http://localhost:5173`, sign in, and `GET /meetings` should return your Teams meetings.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Boot raises `Entra ID config required when use_stub_nodes is false` | One of `AG_ENTRA_*` is unset | Step 6. |
| Boot raises `use_stub_nodes=True is refused when environment='prod'` | Stub auth enabled in prod | Remove `AG_USE_STUB_NODES=1` or set `AG_ENVIRONMENT=dev`. |
| `/runs` returns `401 unauthorized` | Wrong audience or expired token | Check `accessTokenAcceptedVersion: 2` (step 5.1). |
| `KeyError: 'oid'` in backend logs | `oid` not in optional claims | Manifest step 5.2. |
| User gets `consent_required` from OBO | Tenant consent missing | Step 4's admin-consent URL. |
| User can list meetings but recording download is 403 | User is not the meeting organizer | Known v1 limitation. Use a recording you organized, or wait for app-only support. |

---

## Switching to stub mode for tests

`api/.env.test` or env override:

```
AG_USE_STUB_NODES=1
AG_ENVIRONMENT=test
AG_ANTHROPIC_API_KEY=test
```

All `AG_ENTRA_*` may be blank. Boot will refuse if `AG_ENVIRONMENT=prod`. The frontend can also use `?fakeAuth=1` in dev builds; the production bundle strips that branch.
