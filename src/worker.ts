/**
 * Cloudflare Workers entry point
 * Main handler for all HTTP requests, scheduled tasks, and queue messages
 */

import type { Env, VideoQueueMessage } from './models/types';
import { handleAsk } from './handlers/ask';
import { handleModelMetadata } from './handlers/metadata';
import { handleCreditStatus } from './handlers/credits';
import { handleCheckout } from './handlers/checkout';
import { handleAskVideo } from './handlers/ask-video';
import { handleVideoStatus } from './handlers/video-status';
import { handleVideoResult } from './handlers/video-result';
import { handleQueueMessage } from './handlers/queue-handler';
import { discoverLatestModels } from './scheduled/discovery';
import { updateCreditStatus } from './scheduled/credits';

// HTML content for success page
const SUCCESS_PAGE_HTML = `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Payment Successful - Bullshit Detector</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/tailwindcss/2.2.19/tailwind.min.css" rel="stylesheet">
    <style>
        @import url('https://fonts.bunny.net/css2?family=Inter:wght@400;600&display=swap');
        body { font-family: 'Inter', sans-serif; }
    </style>
</head>
<body class="bg-gray-900 text-white flex items-center justify-center min-h-screen">
    <div class="text-center p-8">
        <h1 class="text-4xl font-bold mb-4">Thank You!</h1>
        <p class="text-xl mb-8">Your donation has been received successfully.</p>
        <p class="text-gray-400 mb-8">Your support helps keep the Bullshit Detector running and improving.</p>
        <a href="/" class="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-6 rounded-lg transition">
            Return to Bullshit Detector
        </a>
    </div>
</body>
</html>`;

export default {
  /**
   * HTTP request handler
   */
  async fetch(request: Request, env: Env, _ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);

    // CORS headers
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    };

    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }

    let response: Response;

    // Route handling
    switch (url.pathname) {
      case '/':
        response = new Response('Redirecting to Cloudflare Pages...', {
          status: 302,
          headers: { Location: '/' },
        });
        break;

      case '/ask':
        response = await handleAsk(request, env);
        break;

      case '/ask-video':
        response = await handleAskVideo(request, env);
        break;

      case '/api/model-metadata':
        response = await handleModelMetadata(env);
        break;

      case '/api/credit-status':
        response = await handleCreditStatus(env);
        break;

      case '/api/refresh-models': {
        const authHeader = request.headers.get('Authorization');
        if (!env.ADMIN_SECRET || authHeader !== `Bearer ${env.ADMIN_SECRET}`) {
          response = new Response(JSON.stringify({ error: 'Unauthorized' }), {
            status: 401,
            headers: { 'Content-Type': 'application/json' },
          });
        } else {
          await discoverLatestModels(env);
          const updatedConfig = await env.CACHE.get('model_config', 'json');
          response = new Response(JSON.stringify(updatedConfig), {
            headers: { 'Content-Type': 'application/json' },
          });
        }
        break;
      }

      case '/create-checkout-session':
        response = await handleCheckout(request, env);
        break;

      case '/success':
        response = new Response(SUCCESS_PAGE_HTML, {
          headers: { 'Content-Type': 'text/html' },
        });
        break;

      default: {
        const videoMatch = url.pathname.match(/^\/video\/([0-9a-f-]{36})$/i);
        const statusMatch = url.pathname.match(/^\/api\/video-status\/([0-9a-f-]{36})$/i);

        if (videoMatch) {
          response = await handleVideoResult(videoMatch[1], env);
        } else if (statusMatch) {
          response = await handleVideoStatus(statusMatch[1], env);
        } else {
          response = new Response('Not Found', { status: 404 });
        }
      }
    }

    // Add CORS headers to response
    const headers = new Headers(response.headers);
    Object.entries(corsHeaders).forEach(([key, value]) => headers.set(key, value));

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers,
    });
  },

  /**
   * Queue consumer — processes video analysis jobs message by message.
   * Each message gets its own fresh execution context (no accumulated timeout).
   */
  async queue(batch: MessageBatch<VideoQueueMessage>, env: Env): Promise<void> {
    for (const message of batch.messages) {
      try {
        await handleQueueMessage(message.body, env);
        message.ack();
      } catch {
        // Nack so Cloudflare retries up to max_retries, then dead-letters
        message.retry();
      }
    }
  },

  /**
   * Scheduled task handler (Cron Triggers)
   * Runs daily at 00:00 UTC
   */
  async scheduled(event: ScheduledEvent, env: Env, _ctx: ExecutionContext): Promise<void> {
    console.log('Scheduled task triggered at:', new Date(event.scheduledTime).toISOString());
    await Promise.all([discoverLatestModels(env), updateCreditStatus(env)]);
    console.log('Scheduled task completed');
  },
};
