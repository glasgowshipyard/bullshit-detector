/**
 * /api/model-metadata endpoint handler
 * Returns latest discovered model IDs and documentation URLs
 */

import type { Env } from '../models/types';
import { loadModelConfig } from '../models/config';

export async function handleModelMetadata(env: Env): Promise<Response> {
  try {
    const config = await loadModelConfig(env);

    return new Response(JSON.stringify(config), {
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error: unknown) {
    console.error('Error in /api/model-metadata route:', error);
    const message = error instanceof Error ? error.message : 'Unknown error';
    return new Response(
      JSON.stringify({
        error: 'Internal server error',
        details: message,
      }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}
