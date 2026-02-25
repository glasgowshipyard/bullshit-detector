/**
 * /ask-video endpoint handler
 * Validates the YouTube URL, creates the KV job, and publishes to the video-jobs queue.
 * All processing is done by the queue consumer (queue-handler.ts).
 */

import type { Env, VideoJob } from '../models/types';
import { detectYoutubeUrl, toCanonicalUrl } from '../utils/youtube';

export async function handleAskVideo(request: Request, env: Env): Promise<Response> {
  if (request.method !== 'POST') {
    return new Response(JSON.stringify({ error: 'Method not allowed' }), {
      status: 405,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  try {
    const authHeader = request.headers.get('Authorization');
    const isAdmin = !!(env.ADMIN_SECRET && authHeader === `Bearer ${env.ADMIN_SECRET}`);

    const body = (await request.json()) as { query?: string; claims?: number };
    const query = body.query?.trim();

    if (!query) {
      return new Response(JSON.stringify({ error: 'No query provided' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const videoId = detectYoutubeUrl(query);
    if (!videoId) {
      return new Response(JSON.stringify({ error: 'Not a valid YouTube URL' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const videoUrl = toCanonicalUrl(videoId);

    // Admin can override claims limit: a number (1-50), or 0/omitted = let Gemini decide
    const claimsLimit = isAdmin
      ? body.claims === 0 || body.claims === undefined
        ? null
        : Math.min(Math.max(Number(body.claims), 1), 50)
      : 10;

    // Dedup: return existing job if the same video was analyzed recently
    // Admin bypasses dedup so a fresh analysis can always be forced
    const existingKey = `video_id:${videoId}`;
    if (!isAdmin) {
      const existingJobId = await env.CACHE.get(existingKey);
      if (existingJobId) {
        const existingJob = (await env.CACHE.get(
          `video:${existingJobId}`,
          'json'
        )) as VideoJob | null;
        if (existingJob && existingJob.status !== 'error') {
          return new Response(JSON.stringify({ job_id: existingJobId, cached: true }), {
            headers: { 'Content-Type': 'application/json' },
          });
        }
      }
    }

    // Create new job in KV
    const jobId = crypto.randomUUID();
    const job: VideoJob = {
      status: 'extracting',
      url: videoUrl,
      video_id: videoId,
      created_at: new Date().toISOString(),
    };
    await env.CACHE.put(`video:${jobId}`, JSON.stringify(job), { expirationTtl: 86400 });
    await env.CACHE.put(existingKey, jobId, { expirationTtl: 86400 });

    // Hand off to queue — the consumer handles extraction + verification
    await env.VIDEO_QUEUE.send({ type: 'extract', jobId, videoUrl, claimsLimit });

    const responseBody: Record<string, unknown> = { job_id: jobId, cached: false };
    if (isAdmin) {
      responseBody.admin = true;
      responseBody.claims_limit = claimsLimit;
      responseBody.result_url = `https://bullshitdetector.ai/video/${jobId}`;
    }

    return new Response(JSON.stringify(responseBody), {
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error) {
    console.error('Error in /ask-video:', error);
    const message = error instanceof Error ? error.message : 'Unknown error';
    return new Response(JSON.stringify({ error: 'Internal server error', details: message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}
