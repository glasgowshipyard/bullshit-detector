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
  } catch (error: any) {
    console.error('Error in /api/model-metadata route:', error);
    return new Response(
      JSON.stringify({
        error: 'Internal server error',
        details: error.message,
      }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}
