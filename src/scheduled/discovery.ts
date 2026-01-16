/**
 * Model discovery scheduled task
 * Ported from app.py discover_latest_models() and metadata_scheduler.py
 */

import type { Env, ModelConfig } from '../models/types';

interface APIModel {
  id: string;
  created?: number; // Unix timestamp (OpenAI, Mistral)
  created_at?: string; // ISO string (Anthropic, DeepSeek)
  display_name?: string;
  description?: string;
}

/**
 * Get timestamp from model object
 */
function getTimestamp(model: APIModel): number {
  if (model.created_at) {
    try {
      const dt = new Date(model.created_at.replace('Z', '+00:00'));
      return dt.getTime() / 1000; // Convert to Unix timestamp
    } catch {
      return 0;
    }
  } else if (model.created) {
    return model.created;
  }
  return 0;
}

/**
 * Discover latest model for a specific provider
 */
async function discoverProvider(
  provider: string,
  endpoint: string,
  headers: Record<string, string>,
  filter?: (model: APIModel) => boolean
): Promise<ModelConfig | null> {
  try {
    const response = await fetch(endpoint, {
      method: 'GET',
      headers,
      signal: AbortSignal.timeout(10000),
    });

    if (!response.ok) {
      console.error(`Error querying ${provider} models: HTTP ${response.status}`);
      return null;
    }

    const data = (await response.json()) as any;
    let models: APIModel[] = data.data || [];

    // Apply filter if provided
    if (filter) {
      models = models.filter(filter);
    }

    if (models.length === 0) {
      console.warn(`No models returned from ${provider}`);
      return null;
    }

    // Sort by creation timestamp (newest first)
    const sortedModels = models.sort((a, b) => getTimestamp(b) - getTimestamp(a));
    const latest = sortedModels[0];

    // Extract display name if available
    const displayName = latest.display_name || latest.description || null;

    console.log(`${provider} latest model: ${latest.id} (display: ${displayName})`);

    return {
      id: latest.id,
      display_name: displayName,
      docs_url: '', // Will be set later
    };
  } catch (error: any) {
    console.error(`Error discovering models for ${provider}: ${error.message}`);
    return null;
  }
}

/**
 * Discover latest models from all providers
 */
export async function discoverLatestModels(env: Env): Promise<void> {
  console.log('Starting scheduled model discovery...');

  const docsUrls = {
    openai: 'https://platform.openai.com/docs/models',
    anthropic: 'https://docs.anthropic.com/about-claude/models/overview',
    mistral: 'https://docs.mistral.ai/getting-started/models/',
    deepseek: 'https://api-docs.deepseek.com/models',
    gemini: 'https://ai.google.dev/gemini-api/docs',
  };

  // Discover models from each provider in parallel
  const [openai, anthropic, mistral, deepseek, gemini] = await Promise.all([
    discoverProvider(
      'openai',
      'https://api.openai.com/v1/models',
      { Authorization: `Bearer ${env.OPENAI_API_KEY}` },
      model => model.id.startsWith('gpt-') // Only GPT models
    ),
    discoverProvider(
      'anthropic',
      'https://api.anthropic.com/v1/models',
      {
        'x-api-key': env.CLAUDE_API_KEY,
        'anthropic-version': '2023-06-01',
      },
      model => model.id.startsWith('claude-') // Only Claude models
    ),
    discoverProvider('mistral', 'https://api.mistral.ai/v1/models', {
      Authorization: `Bearer ${env.MISTRAL_API_KEY}`,
    }),
    discoverProvider('deepseek', 'https://api.deepseek.com/v1/models', {
      Authorization: `Bearer ${env.DEEPSEEK_API_KEY}`,
    }),
    discoverProvider(
      'gemini',
      `https://generativelanguage.googleapis.com/v1beta/models?key=${env.GEMINI_API_KEY}`,
      {},
      model => model.id.startsWith('models/gemini-') // Only Gemini models
    ),
  ]);

  // Build config data
  const configData = {
    last_updated: new Date().toISOString(),
    source: 'scheduler_auto_discovery',
    openai: openai
      ? { ...openai, docs_url: docsUrls.openai }
      : { id: 'gpt-4o', display_name: null, docs_url: docsUrls.openai },
    anthropic: anthropic
      ? { ...anthropic, docs_url: docsUrls.anthropic }
      : {
          id: 'claude-sonnet-4-5-20250929',
          display_name: 'Claude Sonnet 4.5',
          docs_url: docsUrls.anthropic,
        },
    mistral: mistral
      ? { ...mistral, docs_url: docsUrls.mistral }
      : { id: 'mistral-large-latest', display_name: null, docs_url: docsUrls.mistral },
    deepseek: deepseek
      ? { ...deepseek, docs_url: docsUrls.deepseek }
      : { id: 'deepseek-chat', display_name: null, docs_url: docsUrls.deepseek },
    gemini: gemini
      ? { ...gemini, docs_url: docsUrls.gemini }
      : { id: 'gemini-2.0-flash-exp', display_name: 'Gemini 2.0 Flash', docs_url: docsUrls.gemini },
  };

  // Save to Workers KV
  try {
    await env.CACHE.put('model_config', JSON.stringify(configData));
    console.log('Model config updated with discovered models');
  } catch (error: any) {
    console.error(`Error saving model config: ${error.message}`);
  }
}
