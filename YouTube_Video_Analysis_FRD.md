# Bullshit Detector — Feature Requirements Document

**Status:** MVP Live
**Last Updated:** February 25, 2026
**Author:** Claude

---

## Executive Summary

Bullshit Detector accepts YouTube URLs and text claims, automatically extracts verifiable factual claims, and verifies each one using a 5-model AI consensus. Results are served on a permanent shareable UUID URL.

This document covers what is built, how it works, the v2.x roadmap (permanent D1 catalogue, user authentication, tiered access, public searchable archive), and the v3.x roadmap (multi-source analysis — Twitter/X, Reddit, news articles, and beyond).

---

## 1. What Is Live Today

### User Flow

1. User pastes a YouTube URL into the input field on bullshitdetector.ai
2. Frontend detects it is a YouTube URL and POSTs to `/ask-video`
3. Server returns `{ job_id: uuid }` immediately — no waiting
4. User is redirected to `/video/{uuid}` which shows live progress
5. Page auto-polls every 3 seconds and updates as claims are verified
6. When complete, full results are displayed with timestamps, verdicts, and expandable model reasoning

### Results Page

**While processing:**

- Spinner with live status label: "Watching the video and extracting claims..." → "Verifying claims with 5 AI models... (3 / 10)"
- Video topic and summary appear as soon as Gemini completes extraction

**When complete:**

- Credibility score (0–100%) with colour coding (green ≥70, amber ≥40, red <40)
- True / False / Uncertain counts
- Claims timeline — one card per claim showing:
  - Timestamp badge (e.g. `2:34`)
  - Claim text, speaker, context
  - Verdict badge + confidence bar
  - Click to expand → each model's full reasoning, colour-coded by provider

**On error:**

- Clear message (e.g. "Gemini could not analyse this video. It may be private or unavailable.")

### Deduplication

If the same video is submitted within 24 hours, the existing job is returned immediately (`cached: true`) — no re-processing, no API cost.

### Admin Override

Authenticated admin requests to `/ask-video` bypass normal limits:

- **Claims limit:** default 10 for all users; admin can specify up to 50 via `"claims"` in the request body
- **Dedup bypass:** admin always gets a fresh analysis regardless of cache
- **Rich response:** includes `result_url` directly so no manual UUID lookup needed

```bash
curl -s -X POST https://bullshitdetector.ai/ask-video \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_SECRET" \
  -d '{"query":"YOUTUBE_URL", "claims": 25}' | jq .
```

```json
{
  "job_id": "uuid",
  "cached": false,
  "admin": true,
  "claims_limit": 25,
  "result_url": "https://bullshitdetector.ai/video/uuid"
}
```

Auth uses the existing `ADMIN_SECRET` Cloudflare secret (same as `/api/refresh-models`). Curl template stored locally in `.dev.vars` (gitignored).

---

## 2. Architecture

### Design Decision: Cloudflare Queues

Video analysis cannot run synchronously. Gemini takes 30–120 seconds to watch a video, and verifying 10 claims sequentially adds another ~70 seconds. Cloudflare Workers have a ~30s execution budget. `ctx.waitUntil` does not reliably extend this for I/O-heavy long-running work.

**Solution:** Cloudflare Queues (`video-jobs`). Each processing step is a separate queue message with its own Worker invocation and its own execution budget. The HTTP request returns immediately; the queue chain does all the work.

```
POST /ask-video { url }
    ↓
[1] HTTP Handler — ask-video.ts
    - Validate YouTube URL, extract video ID
    - Check KV dedup cache (24hr TTL per video ID)
    - Create job in KV: video:{uuid} = { status: 'extracting', ... }
    - Publish: { type: 'extract', jobId, videoUrl }
    - Return { job_id: uuid }          ← response sent immediately

    ↓ [Queue: video-jobs]

[2] extract message — queue-handler.ts (own execution context, up to 120s)
    - Gemini 2.5 Flash watches YouTube video via fileData.fileUri
    - Extracts up to 10 factual claims as JSON (timestamp, speaker, context)
    - Writes KV: { status: 'verifying', claims_found: N, claims: [...unverified] }
    - Publishes: { type: 'verify', jobId, claimIndex: 0 }

    ↓ [Queue: video-jobs]

[3] verify(N) message — queue-handler.ts (own execution context, ~7s each)
    - Reads claim N from KV
    - Calls all 5 models in parallel: OpenAI, Anthropic, Mistral, DeepSeek, Gemini
    - analyzeResponses() → ConsensusAnalysis
    - Writes claim N verdict back to KV
    - If N < last: publishes { type: 'verify', jobId, claimIndex: N+1 }
    - If N = last: computes overall credibility score, writes status: 'complete'

GET /video/{uuid}
    - extracting / verifying: HTML with auto-poll every 3s
    - complete: full claim timeline
    - error: error message with back link

GET /api/video-status/{uuid}
    - JSON polling endpoint: { status, claims_found, claims_verified, video_metadata, claims?, overall? }
```

### Why Gemini Now Participates in Verification

Initially Gemini was excluded from claim verification to conserve its 20 RPD free tier quota for video extraction. With Gemini 3, quota limits are significantly more generous. All 5 models now participate in verification for a stronger consensus signal.

### Queue Configuration (wrangler.toml)

```toml
[[queues.producers]]
binding = "VIDEO_QUEUE"
queue = "video-jobs"

[[queues.consumers]]
queue = "video-jobs"
max_batch_size = 1
max_batch_timeout = 0
max_retries = 2
```

`max_batch_size = 1` ensures each message gets a fully dedicated Worker invocation. `max_retries = 2` dead-letters after 3 total attempts.

### KV Schema (current)

```
video:{uuid} = {
  status: 'extracting' | 'verifying' | 'complete' | 'error',
  url: string,
  video_id: string,
  created_at: string,
  claims_found?: number,
  claims_verified?: number,
  video_metadata?: { title, summary, primary_topic },
  claims?: [{
    id, text, timestamp, speaker, context, type,
    analysis: ConsensusAnalysis,
    responses: Record<provider, ModelResponse>
  }],
  overall?: { credibility_score, false_count, true_count, uncertain_count },
  error?: string
}
TTL: 24 hours

video_id:{videoId} = uuid
TTL: 24 hours (deduplication key)
```

---

## 3. Known Limitations (Current MVP)

- **Claim cap:** Gemini is prompted for "up to 10" claims. Information-dense videos hit this cap consistently. Configurable in future.
- **Political content:** Models return `POLICY_LIMITED` on many political claims. The SOTU and similar content will have a high proportion of unverifiable verdicts.
- **Private/unlisted videos:** Gemini cannot access them — job fails with an error.
- **Very long videos:** Gemini 2.5 Flash supports ~2 hours. Videos beyond that will fail.
- **24hr expiry:** Analyses expire from KV after 24 hours. No permanent storage yet.
- **No rate limiting:** Any IP can submit unlimited videos today.

---

## 4. Roadmap — Next Phase

### 4.1 Permanent Catalogue (D1)

**Problem:** KV TTL means analyses disappear after 24 hours. 10 people wanting to fact-check the same video a week later causes 10 redundant re-analyses at full API cost.

**Solution:** Cloudflare D1 (SQLite) as permanent storage. KV remains as the live job status layer during processing. On completion, results are written to D1 permanently.

**Schema:**

```sql
CREATE TABLE videos (
  video_id       TEXT PRIMARY KEY,
  youtube_url    TEXT NOT NULL,
  first_submitted_at TEXT NOT NULL,
  latest_job_id  TEXT NOT NULL
);

CREATE TABLE evaluations (
  job_id         TEXT PRIMARY KEY,
  video_id       TEXT NOT NULL REFERENCES videos(video_id),
  submitted_by   TEXT,           -- user_id or NULL for anonymous
  submitted_at   TEXT NOT NULL,
  model_snapshot TEXT NOT NULL,  -- JSON: which model versions were used
  results        TEXT NOT NULL,  -- full JSON: claims, overall, video_metadata
  FOREIGN KEY (video_id) REFERENCES videos(video_id)
);
```

`model_snapshot` records which model versions ran the analysis. When a video is re-evaluated 6 months later with different models, the changelog shows _why_ verdicts may have changed.

**Dedup logic with D1:**

- On `/ask-video`, check D1 for existing `video_id` before creating a new job
- If found, return the existing `latest_job_id` (no API calls, no cost)
- Cache hit cost: one D1 read (~microseconds)
- Only genuinely new videos trigger the full queue chain

### 4.2 Public Searchable Archive

The catalogue becomes a public-facing feature: a searchable library of all analysed videos with credibility scores, sortable and filterable.

**Archive features:**

- Search by topic, claim text, channel name, or verdict
- Filter by credibility score range, date range, verdict distribution
- Channel pages — aggregate credibility score across all analysed videos
- Leaderboards — most analysed channels, lowest credibility scores
- Trending — recently submitted, most viewed analyses

**Value proposition:** The catalogue itself becomes the moat. Competitors can copy the tool; they cannot copy 6 months of accumulated analyses. News organisations, researchers, and people fact-checking content they've seen will find value even without submitting new videos.

### 4.3 IP-Based Rate Limiting (Anonymous Users)

**Problem:** Without any rate limiting, a single person can trigger thousands of analyses at full API cost.

**Solution:** One video submission per IP address per 24 hours for unauthenticated users.

**Implementation:**

- Hash the IP (`CF-Connecting-IP` header) before storing — raw IPs are PII
- Store: `ip_submission:{hashed_ip} = "1"` in KV with `TTL: 86400`
- No cleanup needed — expires naturally
- On limit hit, return `{ error: "limit_reached" }` with HTTP 429
- Frontend shows: **"Daily video analysis limit reached. Create a free account to continue."**
- No IP displayed to user — avoids GDPR/PII exposure entirely

**Known tradeoff:** Shared IPs (offices, universities, mobile carrier CGNAT) share the limit. Accepted as a reasonable tradeoff for simplicity.

### 4.4 User Authentication

**Principles:**

- Do not hold PII — no raw emails, no passwords
- Offload identity to OAuth providers
- Store only opaque provider user IDs in D1

**Providers:** Google + GitHub (covers broad and technical audiences respectively)

**Not implementing:** Apple Sign-In (requires compliance on iOS/App Store — not relevant for a web tool), magic links (requires email sending service and you still hold a hashed email which is arguably PII under GDPR given low entropy of email addresses)

**Implementation approach:** Clerk or Auth.js — handle the OAuth dance and session management, surface a stable user ID for D1 references. No PII stored.

**Session storage:** Workers KV — `session:{token} = { user_id, provider, created_at }` with appropriate TTL.

### 4.5 Tiered Access

**Anonymous (no account)**

- 1 video submission per IP per 24 hours
- Results viewable via UUID link (not saved to any account)
- Can browse the public archive
- No re-evaluation

**Free account**

- Up to 5 video submissions per day
- Results saved to account history
- Shareable links
- Download results as JSON
- Can browse full archive with search

**Paid**

- Unlimited video submissions (soft cap: 50/day to prevent abuse)
- Everything in free tier
- Force re-evaluation of any catalogued video
- Download results as PDF
- Higher claim extraction limit (e.g. 20 claims vs 10)
- Early access to new features

**Cost rationale for tiering:** Each video analysis = ~40 LLM API calls. A free user submitting Joe Rogan's entire back catalogue (1000+ episodes) would be financially significant. Daily caps protect against this. The D1 catalogue dedup means most popular videos are free to serve once analysed — marginal cost of a cache hit is a single D1 read.

### 4.6 Re-evaluation and Changelog

Paid users can trigger a fresh analysis of any previously catalogued video. Each re-evaluation creates a new `evaluations` row in D1. The video results page shows a changelog: date of each evaluation, which model versions ran, and whether verdicts changed.

This is more interesting than it sounds — AI model consensus on political or scientific claims shifts over time as models are updated. Surfacing that drift is a genuine differentiator.

---

## 5. Technical Constraints

### Gemini

- Model auto-discovered from API nightly via KV, currently `gemini-3-flash-preview`
- Supports YouTube URLs natively via `fileData.fileUri` — no upload required
- `MEDIA_RESOLUTION_LOW` set — extends effective video length significantly
- One call per video for extraction; also participates in claim verification
- Timeout: 120 seconds (set in extraction fetch call)

### Cloudflare Queues

- 1 million message operations/month free on Workers Paid plan
- Each video = ~12 messages (1 extract + up to 10 verifies + overhead)
- ~80,000 video analyses before hitting the free tier limit
- `max_batch_size = 1` is critical — prevents multiple claims sharing an invocation

### Political Content

Models trained with political neutrality guidelines will return `POLICY_LIMITED` on many political claims. The SOTU and similar content should be expected to return a high proportion of `POLICY_LIMITED` and `UNCERTAIN` verdicts rather than clear TRUE/FALSE. This is a feature not a bug — the system is being honest about what it can verify.

---

## 6. Cost Analysis

### Per-video API costs (approximate)

| Component                                 | Cost       |
| ----------------------------------------- | ---------- |
| Gemini 2.5 Flash — 10min video extraction | ~$0.07     |
| 10 claims × 4 models verification         | ~$0.04     |
| **Total per video**                       | **~$0.11** |

### At scale

| Daily volume   | Monthly cost |
| -------------- | ------------ |
| 10 videos/day  | ~$33/month   |
| 50 videos/day  | ~$165/month  |
| 100 videos/day | ~$330/month  |

D1 catalogue dedup dramatically reduces real costs — popular videos are served from D1 at near-zero marginal cost after the first analysis.

### Break-even

~30 paid subscribers at $10/month covers 100 videos/day running costs.

---

## 7. Open Questions

1. **Claim cap:** Should the 10-claim limit be raised (15–20) for paid users? Gemini decides quality, the cap just limits cost.
2. **Archive browsability:** Should the public archive be live at launch or only after a minimum catalogue size?
3. **Re-evaluation policy:** How often can a paid user re-evaluate the same video? Once per day? Once per model update?
4. **PDF generation:** Client-side (jsPDF) or server-side rendered? Client-side is simpler, server-side is higher quality.
5. **Channel pages:** Requires extracting channel metadata from YouTube — adds a YouTube Data API dependency.
6. **SOTU and political content:** Should political analyses carry an explicit disclaimer about `POLICY_LIMITED` responses?

---

## 8. Implementation Order (Next Phase)

1. **D1 setup** — create database, schema migration, write completed jobs to D1 on queue completion
2. **Remove KV TTL** from video results (or extend significantly) once D1 is the source of truth
3. **IP rate limiting** — hash + KV, 1/day for anonymous, 429 with signup prompt
4. **Auth** — Clerk integration, Google + GitHub OAuth, session KV
5. **Free account tier** — 5/day cap, saved history, JSON download
6. **Public archive** — browsable catalogue with search
7. **Paid tier** — re-evaluation, PDF, higher claim cap

---

## 9. v3.x — Multi-Source Analysis

The worst sources of bullshit are not limited to YouTube. v3.x extends the platform to analyse content from any URL — treating the input field as a universal fact-checking interface rather than a video-specific tool.

### 9.1 Twitter / X Posts (via Nitter)

**The idea:** Users paste a Twitter/X URL. The backend converts it to a Nitter URL, fetches the tweet content, and runs it through the full claim verification pipeline — without sending a single request to X.

**Why Nitter:** Nitter is an open-source Twitter frontend that proxies content without authentication, tracking, or ad revenue for X. Using it as a backend relay is a deliberate architectural choice — we do not want to drive API traffic or engagement signals to a platform whose business model is amplifying the content we're fact-checking.

**Implementation:**

```
POST /ask (Twitter/X URL detected)
    ↓
src/utils/twitter.ts
    - Detect twitter.com or x.com status URL
    - Extract tweet ID
    - Convert to Nitter URL (e.g. nitter.net/user/status/ID)
    ↓
Fetch Nitter page
    - Scrape tweet text, author handle, display name, timestamp
    - Follow quote tweet if present (one level deep)
    - No queue needed — tweet is just text, runs synchronously
    ↓
All 5 models evaluate in parallel
    - Prompt: "Here is a tweet. Extract and evaluate any verifiable factual claims."
    - Same verdict structure: TRUE / FALSE / UNCERTAIN / POLICY_LIMITED / RECUSE
    ↓
Results at /tweet/{uuid}
    - Tweet text displayed verbatim with author attribution
    - Claim cards with verdicts, same UI as video results
```

**Nitter instance resilience:** Public Nitter instances go down. Maintain a short priority list of instances (`nitter.net`, `nitter.privacydev.net`, `nitter.poast.org`) and retry on failure before returning an error.

**Rate limiting:** Same IP-based rules as video analysis once that phase is implemented.

**Dedup:** Cache by tweet ID with 24hr TTL (tweets don't change after posting).

---

### 9.2 Reddit Posts and Threads

Reddit is a significant vector for claim propagation — particularly on politics, science, and health. Posts and top-level comments in threads are often stated as fact with no sourcing.

**Approach:**

- Detect `reddit.com` and `old.reddit.com` URLs
- Use Reddit's own JSON API (`/r/sub/comments/id.json`) — no auth required, no third-party proxy needed
- Extract post title, body text, and optionally top comments
- Same 5-model verification pipeline

**Privacy note:** Reddit's JSON API is public and unauthenticated. No account required, no tracking of the requester.

---

### 9.3 Generic Web Articles

Any news article or webpage URL. The user pastes a link; we fetch and extract the article body, strip boilerplate, and run the text through claim extraction.

**Approach:**

- Detect non-YouTube, non-Twitter, non-Reddit URLs
- Fetch the page, strip navigation/ads/footers using readability heuristics (similar to how read-mode works in browsers)
- Extract main article text
- Run through the same claim extraction and verification pipeline

**Value:** Covers news articles, blog posts, press releases, government statements — any published text.

**Challenge:** Paywalled content cannot be fetched. Return a clear error rather than a partial result.

---

### 9.4 The Bigger Picture

Each new source type follows the same pattern:

```
URL detected → source-specific fetcher → clean text extracted → 5-model consensus → results page
```

The video pipeline (Gemini watching via fileUri) is just one implementation of the fetcher step. Text-based sources are simpler and cheaper — no Gemini extraction call needed, just direct model prompting.

**Unified input field:** The frontend detects URL type automatically. Users don't need to know which pipeline runs — they paste a link, they get a verdict.

**Long-term:** A catalogue that spans YouTube videos, political tweets, Reddit health claims, and news articles is a fundamentally different product from a single-source tool. The public archive (v2.x) becomes a cross-source searchable database of verified claims — categorised by source type, topic, author, and verdict.

---

## 10. Implementation Order (Full Roadmap)

**v2.x (current phase):**

1. D1 setup — permanent catalogue, schema migration
2. Remove KV TTL from video results once D1 is source of truth
3. IP rate limiting — hash + KV, 429 with signup prompt
4. Auth — Clerk/Auth.js, Google + GitHub OAuth
5. Free account tier — 5/day cap, saved history, JSON download
6. Public archive — browsable catalogue with search
7. Paid tier — re-evaluation, PDF, higher claim cap

**v3.x (multi-source):** 8. Twitter/X via Nitter — `/ask` URL detection + Nitter fetch + text models 9. Reddit — JSON API fetch, post + top comments 10. Generic article URLs — readability extraction, any web content 11. Unified archive — cross-source search, claim clustering across source types

---

**Document Version:** 2.1
**Previous Versions:** 2.0 (February 25, 2026), 1.0 (February 21, 2026 — pre-implementation planning)
**Status:** MVP live. v2.x planned. v3.x designed.
