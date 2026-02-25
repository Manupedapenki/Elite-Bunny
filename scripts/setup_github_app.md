# GitHub App Setup Guide

## Step 1: Create the GitHub App

1. Go to **Settings > Developer settings > GitHub Apps > New GitHub App**
2. Fill in the required fields:
   - **App name:** PR Intelligence Bot (or your preferred name)
   - **Homepage URL:** `https://your-domain.com` (or any valid URL)
   - **Webhook URL:** `https://your-server.com/webhooks/github`
     - For local development, use ngrok: `ngrok http 8001` to get a public URL
   - **Webhook secret:** Generate a secure random string and save it as `GITHUB_WEBHOOK_SECRET`

## Step 2: Set Permissions

Under **Permissions & events:**

### Repository permissions:
- **Contents:** Read-only (to fetch file content)
- **Metadata:** Read-only (required by GitHub)
- **Pull requests:** Read & Write (to post review comments)

### Subscribe to events:
- ✅ **Pull request** (opened, synchronize, reopened, closed)
- ✅ **Installation** (created, deleted)

## Step 3: Generate Private Key

1. After creating the app, scroll down to **Private keys**
2. Click **Generate a private key**
3. A `.pem` file will download — save this as `secrets/github-app.pem`

## Step 4: Note the App ID

The App ID is shown at the top of the App settings page. Save it as `GITHUB_APP_ID`.

## Step 5: Install the App

1. From the App settings page, click **Install App** in the left sidebar
2. Choose which repositories to install it on
3. Note the **Installation ID** from the URL after installation
   (e.g., `https://github.com/settings/installations/12345` → Installation ID = 12345)

## Step 6: Configure Environment

```bash
# .env
GITHUB_APP_ID=your_app_id_here
GITHUB_WEBHOOK_SECRET=your_webhook_secret_here
GITHUB_PRIVATE_KEY_PATH=./secrets/github-app.pem
```

## Step 7: Test with ngrok (Local Development)

```bash
# Terminal 1: Start ngrok
ngrok http 8001

# Terminal 2: Start services
docker-compose up -d

# Terminal 3: Update webhook URL in GitHub App settings
# Use the ngrok URL, e.g., https://abc123.ngrok.io/webhooks/github

# Open a PR on your test repo — you should see webhook events in the logs!
docker-compose logs -f webhook-ingestion
```
