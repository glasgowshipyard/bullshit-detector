/**
 * Cloudflare Queue consumer for video analysis jobs.
 *
 * Message flow:
 *   extract  → Gemini watches video, extracts claims, stores in KV,
 *              publishes verify(0)
 *   verify N → Verifies claim N with 4 text models, updates KV,
 *              publishes verify(N+1) or marks job complete
 *
 * Each message runs in its own Worker invocation, so there is no
 * accumulated wall-clock pressure from the initial HTTP request.
 */

import type { Env, VideoJob, VideoClaim, VideoQueueMessage } from '../models/types';
import { queryAllModels } from '../models/query';
import { analyzeResponses } from '../utils/consensus';

// ─── Gemini video extraction ──────────────────────────────────────────────────

function buildExtractionPrompt(claimsLimit: number | null): string {
  const claimsInstruction =
    claimsLimit === null
      ? 'Extract all significant factual claims you find that can be verified as true or false.'
      : `Extract up to ${claimsLimit} significant factual claims that can be verified as true or false.`;

  return `You are an expert fact-checker analyzing a YouTube video for verifiable claims.

Watch the entire video and ${claimsInstruction}

INSTRUCTIONS:
1. Focus on FACTUAL claims only — not opinions, questions, or jokes
2. Note the timestamp when each claim was made (MM:SS format)
3. Identify who made the claim (speaker/narrator/host)
4. Provide brief context for each claim

EXCLUDE:
- Purely subjective opinions ("I think...", "In my view...")
- Future predictions that cannot be verified yet
- Rhetorical questions
- Jokes or obvious sarcasm

FORMAT YOUR RESPONSE AS JSON ONLY — no markdown, no explanation:
{
  "video_summary": "Brief 2-3 sentence summary of video content",
  "primary_topic": "Main subject matter",
  "claims": [
    {
      "claim": "Exact quote or close paraphrase",
      "timestamp": "MM:SS",
      "speaker": "Person who made the claim",
      "context": "What was being discussed",
      "type": "factual"
    }
  ]
}`;
}

async function extractClaimsFromVideo(
  videoUrl: string,
  env: Env,
  claimsLimit: number | null = 10
): Promise<{ video_summary: string; primary_topic: string; claims: VideoClaim[] } | null> {
  try {
    const modelId = 'gemini-3-flash-preview';
    const response = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/${modelId}:generateContent?key=${env.GEMINI_API_KEY}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contents: [
            {
              parts: [
                { text: buildExtractionPrompt(claimsLimit) },
                { fileData: { mimeType: 'video/*', fileUri: videoUrl } },
              ],
            },
          ],
          generationConfig: {
            mediaResolution: 'MEDIA_RESOLUTION_LOW', // enables longer video support
          },
        }),
        signal: AbortSignal.timeout(120000),
      }
    );

    if (!response.ok) {
      const err = await response.text();
      console.error(`Gemini video extraction error: ${err.substring(0, 300)}`);
      return null;
    }

    const data = (await response.json()) as Record<string, unknown>;
    const text = (
      (data['candidates'] as { content: { parts: { text: string }[] } }[])?.[0]?.content?.parts?.[0]
        ?.text ?? ''
    ).trim();

    const jsonText = text.replace(/^```(?:json)?\n?/, '').replace(/\n?```$/, '');
    const parsed = JSON.parse(jsonText) as {
      video_summary: string;
      primary_topic: string;
      claims: {
        claim: string;
        timestamp: string;
        speaker: string;
        context: string;
        type: string;
      }[];
    };

    const claims: VideoClaim[] = parsed.claims.map((c, i) => ({
      id: `claim_${String(i + 1).padStart(3, '0')}`,
      text: c.claim,
      timestamp: c.timestamp,
      speaker: c.speaker,
      context: c.context,
      type: (c.type === 'factual'
        ? 'factual'
        : c.type === 'prediction'
          ? 'prediction'
          : 'opinion') as 'factual' | 'prediction' | 'opinion',
    }));

    return { video_summary: parsed.video_summary, primary_topic: parsed.primary_topic, claims };
  } catch (error) {
    console.error(`Error extracting claims: ${error instanceof Error ? error.message : error}`);
    return null;
  }
}

// ─── Verification prompt ──────────────────────────────────────────────────────

function buildVerificationPrompt(claim: VideoClaim): string {
  return (
    `You are part of the Bullshit Detector multi-model consensus system. ` +
    `Evaluate whether the following question/claim is TRUE or FALSE. Respond with one of: ` +
    `TRUE (the claim is factually correct), FALSE (the claim is factually incorrect), ` +
    `UNCERTAIN (insufficient evidence or unclear), RECUSE (unanswerable/paradoxical), ` +
    `or POLICY_LIMITED (cannot evaluate due to safety/policy constraints). ` +
    `Start your response with your verdict, then explain your reasoning.\n\n` +
    `VIDEO CONTEXT: Claim made at ${claim.timestamp} by ${claim.speaker}. Context: ${claim.context}\n\n` +
    `Claim: ${claim.text}`
  );
}

// ─── KV helpers ───────────────────────────────────────────────────────────────

async function readJob(jobId: string, env: Env): Promise<VideoJob | null> {
  return (await env.CACHE.get(`video:${jobId}`, 'json')) as VideoJob | null;
}

async function writeJob(jobId: string, job: VideoJob, env: Env): Promise<void> {
  await env.CACHE.put(`video:${jobId}`, JSON.stringify(job), { expirationTtl: 86400 });
}

async function failJob(jobId: string, message: string, env: Env): Promise<void> {
  const existing = (await readJob(jobId, env)) ?? ({} as VideoJob);
  await writeJob(jobId, { ...existing, status: 'error', error: message }, env);
}

// ─── Message handlers ─────────────────────────────────────────────────────────

async function handleExtract(
  jobId: string,
  videoUrl: string,
  env: Env,
  claimsLimit: number | null = 10
): Promise<void> {
  console.log(`[queue:extract] ${jobId} claimsLimit=${claimsLimit}`);

  const extraction = await extractClaimsFromVideo(videoUrl, env, claimsLimit);

  if (!extraction) {
    await failJob(
      jobId,
      'Gemini could not analyze this video. It may be private, unavailable, or too long.',
      env
    );
    return;
  }

  const factualClaims = extraction.claims.filter(c => c.type === 'factual');

  if (factualClaims.length === 0) {
    // Nothing to verify — mark complete with empty results
    const base = (await readJob(jobId, env)) ?? ({} as VideoJob);
    await writeJob(
      jobId,
      {
        ...base,
        status: 'complete',
        claims_found: 0,
        claims_verified: 0,
        claims: [],
        video_metadata: {
          title: extraction.primary_topic,
          summary: extraction.video_summary,
          primary_topic: extraction.primary_topic,
        },
        overall: { credibility_score: 0, false_count: 0, true_count: 0, uncertain_count: 0 },
      },
      env
    );
    return;
  }

  // Store extracted (unverified) claims in KV, update status
  const base = (await readJob(jobId, env)) ?? ({} as VideoJob);
  await writeJob(
    jobId,
    {
      ...base,
      status: 'verifying',
      claims_found: factualClaims.length,
      claims_verified: 0,
      claims: factualClaims,
      video_metadata: {
        title: extraction.primary_topic,
        summary: extraction.video_summary,
        primary_topic: extraction.primary_topic,
      },
    },
    env
  );

  // Kick off sequential verification — first claim
  await env.VIDEO_QUEUE.send({ type: 'verify', jobId, claimIndex: 0 });
  console.log(`[queue:extract] ${jobId} → queued verify(0) of ${factualClaims.length}`);
}

async function handleVerify(jobId: string, claimIndex: number, env: Env): Promise<void> {
  console.log(`[queue:verify] ${jobId} claim ${claimIndex}`);

  const job = await readJob(jobId, env);
  if (!job || !job.claims) {
    console.error(`[queue:verify] job ${jobId} not found or has no claims`);
    return;
  }

  const claim = job.claims[claimIndex];
  if (!claim) {
    console.error(`[queue:verify] claim ${claimIndex} not found in job ${jobId}`);
    return;
  }

  // Verify this claim with 4 text models (Gemini excluded — saves quota for video extraction)
  const prompt = buildVerificationPrompt(claim);
  const responses = await queryAllModels(prompt, env, { exclude: ['gemini'] });
  const analysis = analyzeResponses(responses);

  // Write verified claim back into the claims array
  const updatedClaims = [...job.claims];
  updatedClaims[claimIndex] = { ...claim, analysis, responses };

  const verifiedSoFar = updatedClaims.filter(
    c => c.analysis !== null && c.analysis !== undefined
  ).length;
  const isLast = claimIndex === job.claims.length - 1;

  if (isLast) {
    // All claims verified — compute overall and mark complete
    const falseCount = updatedClaims.filter(c => c.analysis?.verdict === 'FALSE').length;
    const trueCount = updatedClaims.filter(c => c.analysis?.verdict === 'TRUE').length;
    const uncertainCount = updatedClaims.filter(
      c => c.analysis?.verdict === 'UNCERTAIN' || c.analysis?.verdict === 'RECUSE'
    ).length;
    const total = updatedClaims.length || 1;

    await writeJob(
      jobId,
      {
        ...job,
        status: 'complete',
        claims_verified: verifiedSoFar,
        claims: updatedClaims,
        overall: {
          credibility_score: Math.round((trueCount / total) * 100),
          false_count: falseCount,
          true_count: trueCount,
          uncertain_count: uncertainCount,
        },
      },
      env
    );
    console.log(`[queue:verify] ${jobId} complete — ${verifiedSoFar} claims`);
  } else {
    // Persist progress and queue the next claim
    await writeJob(
      jobId,
      {
        ...job,
        claims_verified: verifiedSoFar,
        claims: updatedClaims,
      },
      env
    );
    await env.VIDEO_QUEUE.send({ type: 'verify', jobId, claimIndex: claimIndex + 1 });
    console.log(`[queue:verify] ${jobId} claim ${claimIndex} done → queuing ${claimIndex + 1}`);
  }
}

// ─── Main entry point (called from worker queue handler) ─────────────────────

export async function handleQueueMessage(msg: VideoQueueMessage, env: Env): Promise<void> {
  try {
    if (msg.type === 'extract') {
      await handleExtract(msg.jobId, msg.videoUrl, env, msg.claimsLimit ?? 10);
    } else if (msg.type === 'verify') {
      await handleVerify(msg.jobId, msg.claimIndex, env);
    }
  } catch (error) {
    console.error(
      `Queue handler error (${msg.type}):`,
      error instanceof Error ? error.message : error
    );
    // Let the message retry (don't ack) — the queue's max_retries will eventually dead-letter it
    throw error;
  }
}
