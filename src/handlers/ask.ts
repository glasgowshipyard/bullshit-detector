/**
 * /ask endpoint handler
 * Main claim verification endpoint
 */

import type { Env } from '../models/types';
import { preprocessQuery } from '../utils/preprocess';
import { queryAllModels } from '../models/query';
import { analyzeResponses } from '../utils/consensus';

export async function handleAsk(request: Request, env: Env): Promise<Response> {
  if (request.method !== 'POST') {
    return new Response(JSON.stringify({ error: 'Method not allowed' }), {
      status: 405,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  try {
    const body = (await request.json()) as { query?: string };
    const query = body.query?.trim();

    if (!query) {
      return new Response(JSON.stringify({ error: 'No query provided' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Preprocess the query
    const structuredQuery = preprocessQuery(query);

    // Query all models in parallel
    const responses = await queryAllModels(structuredQuery, env);

    // Analyze responses to determine verdict and confidence
    const analysis = analyzeResponses(responses);

    // Return result
    return new Response(
      JSON.stringify({
        query,
        structured_query: structuredQuery,
        responses,
        analysis,
      }),
      {
        headers: { 'Content-Type': 'application/json' },
      }
    );
  } catch (error: unknown) {
    console.error('Error in /ask route:', error);
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
