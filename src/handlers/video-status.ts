/**
 * /api/video-status/:jobId endpoint handler
 * Returns JSON status for polling
 */

import type { Env, VideoJob } from '../models/types';

export async function handleVideoStatus(jobId: string, env: Env): Promise<Response> {
  const raw = await env.CACHE.get(`video:${jobId}`, 'json');

  if (!raw) {
    return new Response(JSON.stringify({ error: 'Job not found' }), {
      status: 404,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  const job = raw as VideoJob;

  // Return a trimmed payload — no need to send all responses in polling calls
  const payload: Record<string, unknown> = {
    status: job.status,
    claims_found: job.claims_found ?? 0,
    claims_verified: job.claims_verified ?? 0,
    video_metadata: job.video_metadata ?? null,
    error: job.error ?? null,
  };

  // Include summarised claims once complete (without full model responses to keep payload small)
  if (job.status === 'complete' && job.claims) {
    payload.claims = job.claims.map(c => ({
      id: c.id,
      text: c.text,
      timestamp: c.timestamp,
      speaker: c.speaker,
      analysis: c.analysis,
    }));
    payload.overall = job.overall ?? null;
  }

  return new Response(JSON.stringify(payload), {
    headers: { 'Content-Type': 'application/json' },
  });
}
