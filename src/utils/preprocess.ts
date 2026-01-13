/**
 * Query preprocessing utilities
 * Ported from preprocess.py
 */

// Standard phrase removals to reduce bias
const REMOVAL_PHRASES = [
  /^Is it true that\s+/i,
  /^I heard that\s+/i,
  /^Some people say\s+/i,
  /^They claim that\s+/i,
  /^Wouldn't you agree that\s+/i,
  /^Isn't it obvious that\s+/i,
  /^Many believe that\s+/i,
];

// Synonym mappings for standardization
const SYNONYM_MAP: Record<string, string> = {
  covid: 'COVID-19',
  'global warming': 'climate change',
  'fake news': 'misinformation',
  hoax: 'false claim',
};

/**
 * Preprocess a user query by:
 * 1. Stripping whitespace
 * 2. Removing bias phrases
 * 3. Standardizing synonyms
 * 4. Wrapping in system prompt for AI models
 *
 * Note: Lemmatization was disabled in Python version, so not implemented here
 */
export function preprocessQuery(query: string): string {
  let processed = query.trim();

  // Remove bias phrases
  for (const pattern of REMOVAL_PHRASES) {
    processed = processed.replace(pattern, '');
  }

  // Replace synonyms (case-insensitive word boundaries)
  for (const [word, replacement] of Object.entries(SYNONYM_MAP)) {
    const regex = new RegExp(`\\b${word}\\b`, 'gi');
    processed = processed.replace(regex, replacement);
  }

  // Wrap in system prompt for consistent evaluation format
  const structuredQuery =
    `You are part of the Bullshit Detector multi-model consensus system. ` +
    `Evaluate this claim's factual accuracy and respond with TRUE, FALSE, UNCERTAIN, ` +
    `RECUSE (if unanswerable/paradoxical), or POLICY_LIMITED (if you cannot evaluate ` +
    `due to safety/policy constraints), followed by your reasoning: ${processed}`;

  return structuredQuery;
}
