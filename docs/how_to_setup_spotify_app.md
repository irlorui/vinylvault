# HOW TO Setup a Spotify App

This guide walks you through creating a Spotify Developer app and getting the credentials VinylVault needs to control playback.

---

## 0. Prerequisites

Although VynilVault execution is completely free, you **need an Spotify Premium Account** in order to register your app in Spotify Developer.

> **Playback requires Spotify Premium** and an active device (desktop app, phone, etc.) open and logged in.

---

## 1. Create a Spotify Developer account

Go to [developer.spotify.com](https://developer.spotify.com) and log in with your regular Spotify account. Accept the Developer Terms of Service if prompted.

---

## 2. Create a new app

1. Click **Create app** in the top-right corner of the dashboard.
2. Fill in the form:
   - **App name** — anything you like, e.g. `VinylVault`
   - **App description** — a short note, e.g. `Local music timeline game`
   - **Redirect URIs** — add exactly: `http://127.0.0.1:8888/callback`
   - **Which API/SDKs are you planning to use?** — select **Web API**
3. Check the Developer Terms box and click **Save**.

---

## 3. Copy your Client ID and Client Secret

After saving, you land on your app's overview page.

1. Your **Client ID** is shown directly on the page — copy it.
2. Click **View client secret** to reveal your **Client Secret** — copy it too.

> Keep your Client Secret private. Never commit it to version control.

---

## 4. Confirm the redirect URI

1. In your app page, click **Edit settings**.
2. Under **Redirect URIs**, verify that `http://127.0.0.1:8888/callback` is listed.
3. If it isn't, add it and click **Save**.

---

## 5. Find your Playlist ID

Open Spotify (desktop or web) and navigate to the playlist you want to use.

- **Desktop app:** right-click the playlist → **Share** → **Copy link to playlist**
- **Web player:** click the `···` menu → **Share** → **Copy link to playlist**

The link looks like this:

```
https://open.spotify.com/playlist/AAAABBBCCC12345?si=...
```

The **Playlist ID** is the segment between `/playlist/` and `?` — in this example: `AAAABBBCCC12345`.

---

## 6. Fill in your `.env` file

Create your own `.config/.env` file from the existing example:

```bash
cp .config/.env.example .env
```

Paste your values according to what was described in previous steps.

---

## 7. Authorise on first run

The first time you run `make run`, Spotify will open a browser tab asking you to authorise the app. Log in and allow access — the token is cached at `.config/.cache` so you won't be asked again.

> **Playback requires Spotify Premium** and an active device (desktop app, phone, etc.) open and logged in.
