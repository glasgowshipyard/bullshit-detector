/**
 * Shared types for model querying
 */

export interface ModelConfig {
  id: string;
  display_name: string | null;
  docs_url: string;
}

export interface FullModelConfig {
  last_updated: string;
  source: string;
  openai: ModelConfig;
  anthropic: ModelConfig;
  mistral: ModelConfig;
  deepseek: ModelConfig;
}

export interface ModelResponse {
  success: boolean;
  content: string | null;
  model: string;
  error?: string;
}

export interface Env {
  OPENAI_API_KEY: string;
  CLAUDE_API_KEY: string;
  MISTRAL_API_KEY: string;
  DEEPSEEK_API_KEY: string;
  STRIPE_SECRET_KEY: string;
  CACHE: KVNamespace;
}
