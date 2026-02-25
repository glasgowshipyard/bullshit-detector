/**
 * AI model query functions
 * Ported from app.py query_model() and model_registry.py
 */

import type { Env, ModelResponse } from './types';
import { loadModelConfig, getValueAtPath } from './config';
import { stripMarkdown } from '../utils/consensus';

/**
 * Query OpenAI API
 */
async function queryOpenAI(prompt: string, env: Env): Promise<ModelResponse> {
  try {
    const config = await loadModelConfig(env);
    const modelId = config.openai.id;

    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${env.OPENAI_API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: modelId,
        messages: [{ role: 'user', content: prompt }],
      }),
      signal: AbortSignal.timeout(30000),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`OpenAI error: ${errorText.substring(0, 200)}`);
      return {
        success: false,
        content: null,
        model: 'openai',
        error: `API returned ${response.status}`,
      };
    }

    const data = (await response.json()) as Record<string, unknown>;
    console.log(`OpenAI using model: ${data['model']}`);
    const content =
      (data['choices'] as { message: { content: string } }[])?.[0]?.message?.content ?? '';

    return {
      success: true,
      content: stripMarkdown(content),
      model: 'openai',
    };
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    console.error(`Error querying OpenAI: ${message}`);
    return {
      success: false,
      content: null,
      model: 'openai',
      error: message,
    };
  }
}

/**
 * Query Anthropic API
 */
async function queryAnthropic(prompt: string, env: Env): Promise<ModelResponse> {
  try {
    const config = await loadModelConfig(env);
    const modelId = config.anthropic.id;

    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'x-api-key': env.CLAUDE_API_KEY,
        'Content-Type': 'application/json',
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: modelId,
        max_tokens: 1000,
        messages: [{ role: 'user', content: prompt }],
      }),
      signal: AbortSignal.timeout(30000),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Anthropic error: ${errorText.substring(0, 200)}`);
      return {
        success: false,
        content: null,
        model: 'anthropic',
        error: `API returned ${response.status}`,
      };
    }

    const data = (await response.json()) as Record<string, unknown>;
    const content = getValueAtPath(data, ['content', 0, 'text']);

    return {
      success: true,
      content: stripMarkdown(content),
      model: 'anthropic',
    };
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    console.error(`Error querying Anthropic: ${message}`);
    return {
      success: false,
      content: null,
      model: 'anthropic',
      error: message,
    };
  }
}

/**
 * Query Mistral API
 */
async function queryMistral(prompt: string, env: Env): Promise<ModelResponse> {
  try {
    const config = await loadModelConfig(env);
    const modelId = config.mistral.id;

    const response = await fetch('https://api.mistral.ai/v1/chat/completions', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${env.MISTRAL_API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: modelId,
        messages: [{ role: 'user', content: prompt }],
        temperature: 0.1,
        max_tokens: 1000,
      }),
      signal: AbortSignal.timeout(30000),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Mistral error: ${errorText.substring(0, 200)}`);
      return {
        success: false,
        content: null,
        model: 'mistral',
        error: `API returned ${response.status}`,
      };
    }

    const data = (await response.json()) as Record<string, unknown>;
    const content = getValueAtPath(data, ['choices', 0, 'message', 'content']);

    return {
      success: true,
      content: stripMarkdown(content),
      model: 'mistral',
    };
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    console.error(`Error querying Mistral: ${message}`);
    return {
      success: false,
      content: null,
      model: 'mistral',
      error: message,
    };
  }
}

/**
 * Query DeepSeek API
 */
async function queryDeepSeek(prompt: string, env: Env): Promise<ModelResponse> {
  try {
    const config = await loadModelConfig(env);
    const modelId = config.deepseek.id;

    const response = await fetch('https://api.deepseek.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${env.DEEPSEEK_API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: modelId,
        messages: [{ role: 'user', content: prompt }],
        temperature: 0.1,
        max_tokens: 1000,
      }),
      signal: AbortSignal.timeout(30000),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`DeepSeek error: ${errorText.substring(0, 200)}`);
      return {
        success: false,
        content: null,
        model: 'deepseek',
        error: `API returned ${response.status}`,
      };
    }

    const data = (await response.json()) as Record<string, unknown>;
    const content = getValueAtPath(data, ['choices', 0, 'message', 'content']);

    return {
      success: true,
      content: stripMarkdown(content),
      model: 'deepseek',
    };
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    console.error(`Error querying DeepSeek: ${message}`);
    return {
      success: false,
      content: null,
      model: 'deepseek',
      error: message,
    };
  }
}

/**
 * Query Google Gemini API
 */
async function queryGemini(prompt: string, env: Env): Promise<ModelResponse> {
  try {
    const config = await loadModelConfig(env);
    const modelId = config.gemini.id;

    const response = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/${modelId}:generateContent?key=${env.GEMINI_API_KEY}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          contents: [
            {
              parts: [{ text: prompt }],
            },
          ],
        }),
        signal: AbortSignal.timeout(30000),
      }
    );

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Gemini error: ${errorText.substring(0, 200)}`);
      return {
        success: false,
        content: null,
        model: 'gemini',
        error: `API returned ${response.status}`,
      };
    }

    const data = (await response.json()) as Record<string, unknown>;
    const content = getValueAtPath(data, ['candidates', 0, 'content', 'parts', 0, 'text']);

    return {
      success: true,
      content: stripMarkdown(content),
      model: 'gemini',
    };
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    console.error(`Error querying Gemini: ${message}`);
    return {
      success: false,
      content: null,
      model: 'gemini',
      error: message,
    };
  }
}

/**
 * Query all AI providers in parallel.
 * Pass `exclude` to skip specific providers.
 */
export async function queryAllModels(
  prompt: string,
  env: Env,
  options: { exclude?: string[] } = {}
): Promise<Record<string, ModelResponse>> {
  const skip = new Set(options.exclude ?? []);

  const providerFns: Record<string, () => Promise<ModelResponse>> = {};
  if (!skip.has('openai')) {
    providerFns.openai = () => queryOpenAI(prompt, env);
  }
  if (!skip.has('anthropic')) {
    providerFns.anthropic = () => queryAnthropic(prompt, env);
  }
  if (!skip.has('mistral')) {
    providerFns.mistral = () => queryMistral(prompt, env);
  }
  if (!skip.has('deepseek')) {
    providerFns.deepseek = () => queryDeepSeek(prompt, env);
  }
  if (!skip.has('gemini')) {
    providerFns.gemini = () => queryGemini(prompt, env);
  }

  const keys = Object.keys(providerFns);
  const results = await Promise.all(keys.map(k => providerFns[k]()));
  return Object.fromEntries(keys.map((k, i) => [k, results[i]]));
}
