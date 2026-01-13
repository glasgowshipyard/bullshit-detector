# Cloudflare Deployment Guide

Simple step-by-step deployment instructions.

## Prerequisites

You need a Cloudflare account with:
- Workers enabled (free)
- Pages enabled (free)

## Step 1: Create KV Namespace (2 minutes)

```bash
wrangler kv:namespace create "CACHE"
wrangler kv:namespace create "CACHE" --preview
```

You'll get output like:
```
{ binding = "CACHE", id = "abc123..." }
{ binding = "CACHE", preview_id = "xyz789..." }
```

Edit `wrangler.toml` and uncomment lines 10-13, adding your IDs:
```toml
[[kv_namespaces]]
binding = "CACHE"
id = "abc123..."
preview_id = "xyz789..."
```

## Step 2: Set Environment Secrets (2 minutes)

```bash
wrangler secret put OPENAI_API_KEY
wrangler secret put CLAUDE_API_KEY
wrangler secret put MISTRAL_API_KEY
wrangler secret put DEEPSEEK_API_KEY
wrangler secret put STRIPE_SECRET_KEY
```

Each command will prompt you to paste the secret value.

## Step 3: Deploy Worker (1 minute)

```bash
wrangler deploy
```

This deploys the API backend. You'll get a URL like:
```
https://bullshit-detector.YOUR-SUBDOMAIN.workers.dev
```

Test it:
```bash
curl https://bullshit-detector.YOUR-SUBDOMAIN.workers.dev/api/model-metadata
```

## Step 4: Deploy Pages (1 minute)

```bash
wrangler pages deploy public --project-name=bullshit-detector
```

This deploys the frontend. You'll get a URL like:
```
https://bullshit-detector.pages.dev
```

## Step 5: Connect Frontend to Backend

The frontend needs to know where the API is.

**Option A: Custom Domain (Recommended)**

If you add a custom domain (like `bullshitdetector.ai`) to Pages, you can use Cloudflare's routing to handle both:

1. In Cloudflare Dashboard → Pages → bullshit-detector → Settings
2. Add custom domain: `bullshitdetector.ai`
3. In Workers & Pages → bullshit-detector (Worker) → Settings → Triggers
4. Add custom route: `bullshitdetector.ai/api/*` and `bullshitdetector.ai/ask` and `bullshitdetector.ai/create-checkout-session`

This way:
- `bullshitdetector.ai/` → Pages (frontend)
- `bullshitdetector.ai/ask` → Worker (API)
- `bullshitdetector.ai/api/*` → Worker (API)

**Option B: Update Frontend Code**

If you want to keep them separate, edit `public/index.html`:

Find the fetch calls (around lines 800-900) and update them:
```javascript
// Add this at the top of the script section:
const API_BASE = 'https://bullshit-detector.YOUR-SUBDOMAIN.workers.dev';

// Then update all API calls:
fetch(`${API_BASE}/ask`, ...)
fetch(`${API_BASE}/api/model-metadata`, ...)
fetch(`${API_BASE}/api/credit-status`, ...)
fetch(`${API_BASE}/create-checkout-session`, ...)
```

Then redeploy Pages:
```bash
wrangler pages deploy public --project-name=bullshit-detector
```

## Architecture

```
User
  │
  ├─→ Cloudflare Pages (https://bullshitdetector.ai)
  │   └── Serves: public/index.html (static frontend)
  │
  └─→ Cloudflare Worker (API endpoints)
      ├── POST /ask
      ├── GET /api/model-metadata
      ├── GET /api/credit-status
      ├── POST /create-checkout-session
      └── Cron: Daily model discovery @ 00:00 UTC
          └── Stores in KV namespace "CACHE"
```

## Verify Deployment

1. **Frontend loads**: Visit `https://bullshit-detector.pages.dev` (or your custom domain)
2. **API works**: Submit a test query
3. **Metadata loads**: Check browser console for successful API calls
4. **Cron scheduled**: In Cloudflare Dashboard → Workers → bullshit-detector → Triggers, verify cron is listed

## Monitor

```bash
# Watch Worker logs in real-time
wrangler tail --format pretty

# Check KV storage
wrangler kv:key get --namespace-id=YOUR_ID "model_config"
```

## Rollback

If anything goes wrong:
1. Heroku app is still running in `archive/heroku/`
2. DNS can be pointed back to Heroku
3. All original Python code is preserved

## Cost

- Worker: Free (100k requests/day)
- Pages: Free (unlimited sites)
- KV: Free (1GB storage, 100k reads/day)
- Cron: Free (3 schedules)

**Total: $0/month**

## Next Steps After Testing

1. Test thoroughly on Cloudflare deployment
2. Monitor for 24-48 hours
3. If stable, point DNS to Cloudflare
4. Wait 1 week, then decommission Heroku

---

**Current Status:**
- ✅ Worker code ready (`src/worker.ts`)
- ✅ Frontend ready (`public/index.html`)
- ⏳ Waiting for: KV namespace creation & deployment
