/**
 * /api/credit-status endpoint handler
 * Returns current API credit balance
 */

import type { Env } from '../models/types';

export async function handleCreditStatus(env: Env): Promise<Response> {
  try {
    const status = await env.CACHE.get('credit_status', 'json');

    if (!status) {
      return new Response(
        JSON.stringify({
          balance: 0,
          currency: 'USD',
          last_updated: null,
        }),
        {
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    return new Response(JSON.stringify(status), {
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error: unknown) {
    console.error('Error in /api/credit-status route:', error);
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
