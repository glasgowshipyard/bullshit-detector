# SRS & MVP SPEC: BullshitDetector Live (BDL) Expansion

## 1. PROJECT OVERVIEW
* **Purpose:** To expand bullshitdetector.ai from a manual claim-entry site into an automated, real-time monitoring tool for live video/audio streams.
* **Core Objective:** Reduce "Truth Latency" to < 20 seconds from the moment a claim is spoken to the moment it is verified by the multi-model jury.

---

## 2. FUNCTIONAL REQUIREMENTS (FR)

### FR-1: Stream Ingestion
* **Input:** The system shall accept a URL from supported platforms (YouTube, X, Twitch).
* **Processing:** The system shall utilize `yt-dlp` to extract a raw audio-only stream.
* **Output:** Continuous 16-bit PCM audio (16kHz mono) piped to the Dispatcher.

### FR-2: Claim Dispatcher (Gemini 2.5 Flash)
* **Context Management:** The system shall maintain a persistent session (up to 1M tokens) to ensure pronoun resolution (e.g., "He" -> "Candidate X") across long-form content.
* **Extraction Logic:** The system shall identify "Empirical Claims" (verifiable facts, dates, statistics) while ignoring rhetorical fluff, jokes, and subjective opinions.
* **Data Packaging:** Claims must be emitted as a JSON object containing:
    * `speaker_id`: Unique identifier for the current speaker.
    * `claim_text`: Normalized, de-contextualized claim string.
    * `timestamp`: Relative time in the stream.

### FR-3: Multi-Model Validation Hub (Cloudflare Worker)
* **Fan-Out:** Upon receiving a JSON claim, the system shall trigger parallel requests to the existing model ensemble (GPT-4o, Claude 3.5, Mistral, DeepSeek).
* **Consensus Algorithm:** The system shall aggregate verdicts and evidence to produce a final "Aggregated Truth Score."

### FR-4: Real-Time UI Update
* **Communication:** The system shall utilize WebSockets to push new claims and their verification status to the frontend.
* **Display:** The UI shall display a "Live Feed" list where claims appear instantly and update status as models return results.

---

## 3. NON-FUNCTIONAL REQUIREMENTS (NFR)

* **Latency:** The "Ear-to-Screen" delay for a finalized claim verification shall not exceed 25 seconds.
* **Cost Optimization:** The Dispatcher shall implement a "Significance Filter" to only trigger the full multi-model jury for high-impact empirical claims.
* **Reliability:** The system must handle "Stream Reconnects" without losing the historical context of the debate.

---

## 4. MVP ARCHITECTURE & STACK

| Component | Technology | Role |
| :--- | :--- | :--- |
| **Ingestion** | Python / `yt-dlp` / `ffmpeg` | Raw audio extraction. |
| **Dispatcher** | Gemini 2.5 Flash (Live API) | Context-aware claim extraction. |
| **Validation Hub** | Cloudflare Workers (TypeScript) | Multi-model orchestration (current site logic). |
| **Database/Cache** | Redis / KV Storage | Caching claims to avoid redundant API calls. |
| **Frontend** | React / WebSockets | Real-time "Truth Feed" dashboard. |

---

## 5. MVP MILESTONES (THE 30-DAY SPRINT)

1.  **Milestone 1 (The Pipe):** Establish a stable Python process that pipes YouTube live audio into the Gemini Live API and prints "Claim Detected" to the console.
2.  **Milestone 2 (The JSON Bridge):** Configure the Dispatcher to POST these claims to your existing Cloudflare Worker `/ask` endpoint.
3.  **Milestone 3 (The Feed):** Build a basic "Live Feed" component on bullshitdetector.ai that updates via WebSockets as claims are processed.
