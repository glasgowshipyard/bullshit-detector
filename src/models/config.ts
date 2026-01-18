/**
 * Model configuration and registry
 * Ported from model_registry.py
 */

import type { Env, FullModelConfig } from './types';

// Fallback configuration (last known good)
const FALLBACK_CONFIG: FullModelConfig = {
  last_updated: '2025-10-20T00:00:00Z',
  source: 'last_known_good_fallback',
  openai: {
    id: 'gpt-4o',
    display_name: null,
    docs_url: 'https://platform.openai.com/docs/models',
  },
  anthropic: {
    id: 'claude-sonnet-4-5-20250929',
    display_name: 'Claude Sonnet 4.5',
    docs_url: 'https://docs.anthropic.com/about-claude/models/overview',
  },
  mistral: {
    id: 'mistral-large-latest',
    display_name: null,
    docs_url: 'https://docs.mistral.ai/getting-started/models/',
  },
  deepseek: {
    id: 'deepseek-chat',
    display_name: null,
    docs_url: 'https://api-docs.deepseek.com/models',
  },
  gemini: {
    id: 'gemini-2.0-flash-exp',
    display_name: 'Gemini 2.0 Flash',
    docs_url: 'https://ai.google.dev/gemini-api/docs',
  },
};

/**
 * Load model configuration from Workers KV
 * Falls back to hardcoded config if KV is empty
 */
export async function loadModelConfig(env: Env): Promise<FullModelConfig> {
  try {
    const config = await env.CACHE.get('model_config', 'json');
    if (config) {
      return config as FullModelConfig;
    }
  } catch (error) {
    console.error('Error loading model config from KV:', error);
  }

  return FALLBACK_CONFIG;
}

/**
 * Get a value from a nested object using a path
 * Example: path = ['choices', 0, 'message', 'content']
 */
export function getValueAtPath(
  obj: Record<string, unknown> | unknown[],
  path: (string | number)[]
): string {
  let current: unknown = obj;
  for (const key of path) {
    if (Array.isArray(current)) {
      current = current[Number(key)];
    } else if (current && typeof current === 'object') {
      current = (current as Record<string, unknown>)[key];
    }
  }
  return current as string;
}
