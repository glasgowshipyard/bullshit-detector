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
  gemini: ModelConfig;
}

export interface ModelResponse {
  success: boolean;
  content: string | null;
  model: string;
  error?: string;
}

export interface VideoClaim {
  id: string;
  text: string;
  timestamp: string;
  speaker: string;
  context: string;
  type: 'factual' | 'prediction' | 'opinion';
  analysis?: import('../utils/consensus').ConsensusAnalysis;
  responses?: Record<string, ModelResponse>;
}

export interface VideoJobMetadata {
  title: string;
  summary: string;
  primary_topic: string;
}

export interface VideoOverall {
  credibility_score: number;
  false_count: number;
  true_count: number;
  uncertain_count: number;
}

export interface VideoJob {
  status: 'pending' | 'extracting' | 'verifying' | 'complete' | 'error';
  url: string;
  video_id: string;
  created_at: string;
  claims_found?: number;
  claims_verified?: number;
  video_metadata?: VideoJobMetadata;
  claims?: VideoClaim[];
  overall?: VideoOverall;
  error?: string;
}

export type VideoQueueMessage =
  | { type: 'extract'; jobId: string; videoUrl: string; claimsLimit?: number | null }
  | { type: 'verify'; jobId: string; claimIndex: number };

export interface Env {
  OPENAI_API_KEY: string;
  CLAUDE_API_KEY: string;
  MISTRAL_API_KEY: string;
  DEEPSEEK_API_KEY: string;
  GEMINI_API_KEY: string;
  STRIPE_SECRET_KEY: string;
  ADMIN_SECRET: string;
  CACHE: KVNamespace;
  VIDEO_QUEUE: Queue<VideoQueueMessage>;
}
