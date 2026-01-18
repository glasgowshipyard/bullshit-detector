/**
 * Consensus analysis utilities
 * Ported from app.py analyze_responses() function
 */

export type Classification = 'TRUE' | 'FALSE' | 'UNCERTAIN' | 'RECUSE' | 'POLICY_LIMITED';
export type ConfidenceLevel = 'VERY HIGH' | 'HIGH' | 'MEDIUM' | 'LOW' | 'VERY LOW';

export interface ModelResponse {
  success: boolean;
  content: string | null;
  model: string;
  error?: string;
}

export interface ConsensusAnalysis {
  verdict: Classification;
  confidence_percentage: number;
  confidence_level: ConfidenceLevel;
  model_judgments: Record<string, Classification>;
  policy_limited_responses: string[];
  uncertain_responses: string[];
}

/**
 * Strip markdown formatting from text
 */
export function stripMarkdown(text: string): string {
  if (!text) {
    return text;
  }

  let processed = text;

  // Remove bold/italic formatting
  processed = processed.replace(/\*\*(.*?)\*\*/g, '$1');
  processed = processed.replace(/\*(.*?)\*/g, '$1');

  // Remove headers
  processed = processed.replace(/^#+\s+/gm, '');

  // Remove code blocks
  processed = processed.replace(/```.*?```/gs, '');

  // Remove inline code
  processed = processed.replace(/`(.*?)`/g, '$1');

  return processed;
}

/**
 * Detect if a model is recusing itself from judgment
 */
function detectRecusal(content: string): boolean {
  const recusalPatterns = [
    /\brecuse\b/i,
    /\bparadox\b/i,
    /\bself-referential\b/i,
    /\bcannot be definitively labeled\b/i,
    /\binherently unanswerable\b/i,
    /\bphilosophical\b.*\bobjection\b/i,
    /\bcategory error\b/i,
    /\bunanswerable by design\b/i,
  ];

  return recusalPatterns.some(pattern => pattern.test(content));
}

/**
 * Detect if a model is declining due to policy constraints
 */
function detectPolicyLimitation(content: string): boolean {
  const policyPatterns = [
    /\bpolicy_limited\b/i,
    /\bi (don't|do not) feel comfortable\b/i,
    /\bi apologize.*cannot\b/i,
    /\bnot appropriate to discuss\b/i,
    /\brecommend consulting\b/i,
    /\bwould suggest referring to\b/i,
    /\bplease consult official sources\b/i,
    /\bit's important to rely on\b/i,
    /\bi'm not comfortable speculating\b/i,
  ];

  return policyPatterns.some(pattern => pattern.test(content));
}

// Uncertainty patterns that indicate factual uncertainty rather than policy limits
const UNCERTAINTY_PATTERNS = [
  'cannot be definitively answered',
  'complex issue',
  'not enough evidence',
  'remains disputed',
  'difficult to determine',
  'would require more information',
  'cannot be answered with a simple',
  'insufficient evidence',
  'uncertain',
  'depends on',
  'ambiguous',
  'unclear',
  'debated',
  'controversial',
];

/**
 * Check if content contains uncertainty markers
 */
function hasUncertainty(content: string): boolean {
  const contentLower = content.toLowerCase();
  return UNCERTAINTY_PATTERNS.some(pattern => contentLower.includes(pattern));
}

/**
 * Check if content contains FALSE verdict (not negated)
 */
function hasFalseVerdict(content: string): boolean {
  return (
    content.includes('FALSE') && !content.includes('NOT FALSE') && !content.includes("ISN'T FALSE")
  );
}

/**
 * Check if content contains TRUE verdict (not negated)
 */
function hasTrueVerdict(content: string): boolean {
  return (
    content.includes('TRUE') && !content.includes('NOT TRUE') && !content.includes("ISN'T TRUE")
  );
}

/**
 * Extract classification from a single model response
 */
function classifyResponse(content: string): {
  classification: Classification;
  isUncertain: boolean;
} {
  if (detectRecusal(content)) {
    return { classification: 'RECUSE', isUncertain: false };
  }

  if (detectPolicyLimitation(content)) {
    return { classification: 'POLICY_LIMITED', isUncertain: false };
  }

  const contentUpper = content.toUpperCase();
  const uncertain = hasUncertainty(content);

  if (hasFalseVerdict(contentUpper)) {
    return {
      classification: uncertain ? 'UNCERTAIN' : 'FALSE',
      isUncertain: uncertain,
    };
  }

  if (hasTrueVerdict(contentUpper)) {
    return {
      classification: uncertain ? 'UNCERTAIN' : 'TRUE',
      isUncertain: uncertain,
    };
  }

  // Default to UNCERTAIN if no clear verdict
  return { classification: 'UNCERTAIN', isUncertain: true };
}

/**
 * Extract judgments from all model responses
 */
function extractJudgments(responses: Record<string, ModelResponse>): {
  judgments: Record<string, Classification>;
  policyLimited: string[];
  uncertain: string[];
} {
  const judgments: Record<string, Classification> = {};
  const policyLimited: string[] = [];
  const uncertain: string[] = [];

  for (const [model, response] of Object.entries(responses)) {
    if (!response.success || !response.content) {
      continue;
    }

    const { classification, isUncertain } = classifyResponse(response.content);
    judgments[model] = classification;

    if (classification === 'POLICY_LIMITED') {
      policyLimited.push(model);
    } else if (isUncertain || classification === 'UNCERTAIN') {
      uncertain.push(model);
    }
  }

  return { judgments, policyLimited, uncertain };
}

/**
 * Determine the majority verdict from judgment counts
 */
function determineMajorityVerdict(
  judgmentCounts: Record<Classification, number>,
  totalModels: number
): Classification {
  // If significant uncertainty, verdict is UNCERTAIN
  if (judgmentCounts.UNCERTAIN >= totalModels / 3 || judgmentCounts.UNCERTAIN >= 2) {
    return 'UNCERTAIN';
  }

  // If tie between TRUE and FALSE, use UNCERTAIN
  if (judgmentCounts.TRUE === judgmentCounts.FALSE && judgmentCounts.TRUE > 0) {
    return 'UNCERTAIN';
  }

  // Otherwise use the most common verdict
  return Object.entries(judgmentCounts).reduce((a, b) =>
    b[1] > a[1] ? b : a
  )[0] as Classification;
}

interface ConfidenceParams {
  majorityVerdict: Classification;
  judgmentCounts: Record<Classification, number>;
  totalModels: number;
  policyLimited: string[];
  judgments: Record<string, Classification>;
}

/**
 * Calculate confidence percentage based on agreement and uncertainty
 */
function calculateConfidence(params: ConfidenceParams): number {
  const { majorityVerdict, judgmentCounts, totalModels, policyLimited, judgments } = params;

  if (totalModels === 0) {
    return 0;
  }

  const agreementCount = judgmentCounts[majorityVerdict];

  if (majorityVerdict === 'UNCERTAIN') {
    return Math.min(70, (agreementCount / totalModels) * 100);
  }

  // For TRUE/FALSE verdicts, account for policy-limited responses
  const policyAligned = policyLimited.filter(model => judgments[model] === majorityVerdict).length;
  const nonPolicyTotal = totalModels - policyLimited.length;

  let confidence: number;

  if (nonPolicyTotal > 0) {
    const baseConfidence = ((agreementCount - policyAligned) / nonPolicyTotal) * 100;
    const policyBonus = (policyAligned / totalModels) * 20;
    confidence = Math.min(100, baseConfidence + policyBonus);
  } else {
    confidence = (agreementCount / totalModels) * 90;
  }

  // Apply uncertainty penalty
  if (judgmentCounts.UNCERTAIN > 0) {
    const uncertaintyPenalty = (judgmentCounts.UNCERTAIN / totalModels) * 30;
    confidence = Math.max(40, confidence - uncertaintyPenalty);
  }

  return confidence;
}

/**
 * Determine confidence level text from percentage
 */
function getConfidenceLevel(confidence: number): ConfidenceLevel {
  if (confidence >= 90) {
    return 'VERY HIGH';
  }
  if (confidence >= 70) {
    return 'HIGH';
  }
  if (confidence >= 50) {
    return 'MEDIUM';
  }
  if (confidence >= 30) {
    return 'LOW';
  }
  return 'VERY LOW';
}

/**
 * Analyze responses from multiple models to determine verdict and confidence
 */
export function analyzeResponses(responses: Record<string, ModelResponse>): ConsensusAnalysis {
  const { judgments, policyLimited, uncertain } = extractJudgments(responses);

  // Count substantive judgments (exclude RECUSE and POLICY_LIMITED)
  const substantiveJudgments = Object.fromEntries(
    Object.entries(judgments).filter(([_, v]) => v !== 'RECUSE' && v !== 'POLICY_LIMITED')
  );

  const judgmentCounts = {
    TRUE: 0,
    FALSE: 0,
    UNCERTAIN: 0,
    RECUSE: 0,
    POLICY_LIMITED: 0,
  };
  for (const judgment of Object.values(substantiveJudgments)) {
    judgmentCounts[judgment as Classification]++;
  }

  const totalModels = Object.keys(substantiveJudgments).length;
  const majorityVerdict = determineMajorityVerdict(judgmentCounts, totalModels);
  const confidence = calculateConfidence({
    majorityVerdict,
    judgmentCounts,
    totalModels,
    policyLimited,
    judgments,
  });
  const confidenceLevel = getConfidenceLevel(confidence);

  return {
    verdict: majorityVerdict,
    confidence_percentage: Math.round(confidence),
    confidence_level: confidenceLevel,
    model_judgments: judgments,
    policy_limited_responses: policyLimited,
    uncertain_responses: uncertain,
  };
}
