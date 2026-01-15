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
    `Evaluate whether the following claim is TRUE or FALSE. Respond with one of: ` +
    `TRUE (the claim is factually correct), FALSE (the claim is factually incorrect), ` +
    `UNCERTAIN (insufficient evidence or unclear), RECUSE (unanswerable/paradoxical), ` +
    `or POLICY_LIMITED (cannot evaluate due to safety/policy constraints). ` +
    `Start your response with your verdict, then explain your reasoning.\n\n` +
    `Claim: ${processed}`;

  return structuredQuery;
}
