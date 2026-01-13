# Cloudflare Migration Reference

Complete migration from Heroku (Python/Flask) to Cloudflare (TypeScript/Workers + Pages).

## What Was Done

### Code Migration
- **Backend:** Python/Flask (`app.py`, 633 lines) → TypeScript Workers (`src/worker.ts`)
- **Preprocessing:** `preprocess.py` → `src/utils/preprocess.ts` (removed NLTK dependency, was disabled anyway)
- **Consensus Logic:** `app.py:analyze_responses()` → `src/utils/consensus.ts`
- **AI Providers:** `model_registry.py` + `app.py:query_model()` → `src/models/query.ts`
- **Scheduled Tasks:** APScheduler → Cron Triggers (`src/scheduled/discovery.ts`, `src/scheduled/credits.ts`)
- **Storage:** `/tmp/*.json` → Workers KV namespace "CACHE"
- **Frontend:** `templates/index.html` → `public/index.html` (copied, not moved - Heroku still works)

### File Structure
```
src/
├── worker.ts              # Main Workers entry point, all HTTP routes
├── handlers/
│   ├── ask.ts            # POST /ask - main claim verification
│   ├── checkout.ts       # POST /create-checkout-session - Stripe
│   ├── credits.ts        # GET /api/credit-status
│   └── metadata.ts       # GET /api/model-metadata
├── models/
│   ├── config.ts         # Load model config from KV
│   ├── query.ts          # Query all 4 AI providers
│   └── types.ts          # TypeScript types
├── utils/
│   ├── consensus.ts      # Analyze responses, calculate verdict
│   └── preprocess.ts     # Query preprocessing
└── scheduled/
    ├── credits.ts        # Update DeepSeek balance (daily cron)
    └── discovery.ts      # Discover latest models (daily cron)

public/
└── index.html            # Static frontend (copy of templates/index.html)

archive/heroku/           # Original Python code (UNTOUCHED - rollback available)
├── app.py
├── preprocess.py
├── model_registry.py
├── metadata_scheduler.py
├── Procfile
└── requirements.txt
```

## Architecture Changes

### Heroku (Old)
```
User → Heroku Dyno (Python/Flask)
       ├── Gunicorn (port 5000)
       ├── APScheduler (background tasks)
       └── /tmp/model_config.json (ephemeral)
```

### Cloudflare (New)
```
User → Cloudflare Pages (static index.html)
       └── API calls to Cloudflare Worker
           ├── Routes: /ask, /api/*, /create-checkout-session
           ├── Cron Triggers: 0 0 * * * (daily at 00:00 UTC)
           └── Workers KV: "CACHE" namespace
               ├── model_config (discovered model IDs)
               └── credit_status (DeepSeek balance)
```

## Key Differences

| Aspect | Heroku | Cloudflare |
|--------|--------|-----------|
| Language | Python 3.8+ | TypeScript |
| Framework | Flask | Workers (native) |
| Scheduled Tasks | APScheduler (in-process) | Cron Triggers (native) |
| Storage | /tmp (ephemeral) | Workers KV (persistent) |
| Preprocessing | NLTK (disabled) | Regex only |
| Cold Start | ~10s | <100ms |
| Cost | $7-25/month | $0/month |

## Deployment Order (IMPORTANT)

1. **Deploy Worker first** - Get API working and test it
2. **Verify Worker** - All endpoints respond correctly
3. **Deploy Pages** - Serve frontend
4. **Test integration** - Frontend can call Worker API
5. **Monitor** - Watch for 24-48 hours
6. **DNS cutover** - Point domain to Cloudflare (if using custom domain)
7. **Keep Heroku running** - Don't shut down for at least 1 week
8. **Decommission Heroku** - Only after confirming stability

## Rollback Plan

### If Deployment Fails
- Heroku app still running at `archive/heroku/`
- Original `templates/index.html` untouched
- Can redeploy Heroku from archive: `git checkout HEAD~1 && git push heroku main`

### If Issues Found After Cutover
1. Point DNS back to Heroku (5-60 min propagation)
2. Scale up Heroku dyno if scaled down
3. Debug Cloudflare offline
4. Retry deployment after fixes

### Rollback Triggers
- Error rate >5% over 1 hour
- Any endpoint completely non-functional
- Payment processing broken
- Model queries timing out consistently

## Testing Checklist

### Before DNS Cutover
- [ ] Worker deployed successfully
- [ ] All 5 secrets set (OPENAI_API_KEY, CLAUDE_API_KEY, MISTRAL_API_KEY, DEEPSEEK_API_KEY, STRIPE_SECRET_KEY)
- [ ] KV namespace created and bound
- [ ] `/ask` endpoint returns results (test with curl)
- [ ] `/api/model-metadata` returns model config
- [ ] `/api/credit-status` returns balance
- [ ] Stripe checkout creates sessions (test mode)
- [ ] Cron trigger scheduled in dashboard
- [ ] Pages deployment serves index.html
- [ ] Frontend can call Worker API
- [ ] All 4 AI providers respond
- [ ] Consensus algorithm matches Heroku results

### After DNS Cutover
- [ ] Production domain loads frontend
- [ ] Queries complete end-to-end
- [ ] Payment flow works
- [ ] No console errors
- [ ] Mobile responsive
- [ ] Dark/light mode works
- [ ] Monitor logs for 24 hours (`wrangler tail`)

## Known Issues & Solutions

### Issue: Frontend can't reach Worker API
**Solution:** Either:
- Add Worker routes to same domain via Cloudflare routing, OR
- Update `public/index.html` API calls to point to Worker URL

### Issue: KV namespace not found
**Solution:** Ensure `wrangler.toml` has correct KV namespace IDs from `wrangler kv:namespace create`

### Issue: Secrets not accessible
**Solution:** Run `wrangler secret put <KEY>` for each required key

### Issue: Cron not running
**Solution:** Check Cloudflare dashboard → Workers → Triggers, verify cron expression is correct

### Issue: TypeScript errors during deployment
**Solution:** Run `npm run typecheck` locally first

### Issue: Worker timeout (30s limit)
**Solution:** AI queries take 15-20s normally. If timing out:
- Check API keys are valid
- Verify network connectivity
- Consider upgrading to Workers Paid ($5/month) for longer timeout

## Environment Variables

### Required Secrets (set via `wrangler secret put`)
```
OPENAI_API_KEY          # OpenAI API key
CLAUDE_API_KEY          # Anthropic API key
MISTRAL_API_KEY         # Mistral API key
DEEPSEEK_API_KEY        # DeepSeek API key
STRIPE_SECRET_KEY       # Stripe secret key
```

### Local Development (.dev.vars)
Create `.dev.vars` in project root:
```
OPENAI_API_KEY=sk-...
CLAUDE_API_KEY=sk-ant-...
MISTRAL_API_KEY=...
DEEPSEEK_API_KEY=...
STRIPE_SECRET_KEY=sk_test_...
```
**⚠️ Never commit this file - already in .gitignore**

## Monitoring

### View Worker Logs
```bash
wrangler tail --format pretty
```

### Check KV Storage
```bash
# List all keys
wrangler kv:key list --namespace-id=YOUR_KV_ID

# Get specific value
wrangler kv:key get --namespace-id=YOUR_KV_ID "model_config"
wrangler kv:key get --namespace-id=YOUR_KV_ID "credit_status"
```

### Cloudflare Dashboard Metrics
- Workers & Pages → bullshit-detector → Metrics
- Monitor: Requests, Errors, CPU time, KV operations

### Expected Behavior
- **Cron triggers:** Run daily at 00:00 UTC
- **Model config updates:** Every 24 hours
- **Credit status updates:** Every 24 hours
- **Average response time:** 15-20 seconds (AI queries in parallel)
- **KV reads per request:** 1-2 (model config lookup)
- **KV writes:** 2 per day (cron tasks)

## Cost Monitoring

### Free Tier Limits
- Workers requests: 100,000/day
- KV reads: 100,000/day
- KV writes: 1,000/day
- KV storage: 1GB
- Cron Triggers: 3 schedules

### Current Usage (Estimated)
- Workers requests: ~1,000-5,000/day (depends on traffic)
- KV reads: ~1,000-5,000/day (1 per /ask request)
- KV writes: 2/day (cron tasks only)
- KV storage: ~5KB (2 JSON files)
- Cron schedules: 1 (runs 2 tasks)

**Should stay well within free tier.**

## Performance Comparison

### Heroku
- Cold start: 10-15 seconds
- Request latency: 50-100ms (before AI calls)
- AI query time: 15-20 seconds (parallel)
- Total: ~16-21 seconds

### Cloudflare
- Cold start: <100ms
- Request latency: 10-20ms (edge)
- AI query time: 15-20 seconds (parallel)
- Total: ~15-20 seconds

**User-facing improvement:** ~1 second faster + global edge caching

## Important Notes

### DO NOT
- Delete `archive/heroku/` directory
- Delete `templates/index.html` (Heroku still uses it)
- Shut down Heroku immediately after Cloudflare deploy
- Force-push to main branch (could lose rollback point)
- Commit `.dev.vars` file

### DO
- Keep Heroku running for at least 1 week after cutover
- Monitor error rates daily for first week
- Test payment flow in Stripe test mode before production
- Verify cron tasks are running (check KV updates)
- Back up any manual configuration in Cloudflare dashboard

## Support & Debugging

### Logs Location
- **Worker logs:** `wrangler tail` or Cloudflare dashboard
- **Build logs:** Wrangler CLI output during deployment
- **Browser console:** Frontend errors and API responses

### Common Debug Commands
```bash
# Test Worker locally
wrangler dev

# Check TypeScript compilation
npm run typecheck

# Deploy to production
wrangler deploy

# View real-time logs
wrangler tail --format pretty

# Test API endpoint
curl https://YOUR-WORKER.workers.dev/ask -X POST -H "Content-Type: application/json" -d '{"query":"test"}'
```

## Timeline

- **Code migration:** ~15 hours (completed)
- **Deployment setup:** ~10-15 minutes (you do this)
- **Testing period:** 24-48 hours
- **Monitoring period:** 1 week
- **Total cutover time:** ~1-2 weeks (safe approach)

## Success Criteria

Migration is successful when:
- [ ] All endpoints functional for 48 hours
- [ ] Error rate <1%
- [ ] Response times comparable to Heroku
- [ ] Payments processing successfully
- [ ] Cron tasks running daily
- [ ] No user-reported issues
- [ ] Cost = $0/month

---

**Status:** Code complete, ready for deployment.
**Next step:** See DEPLOY.md for deployment commands.
**Questions:** Check Cloudflare Workers docs or ask Claude.
