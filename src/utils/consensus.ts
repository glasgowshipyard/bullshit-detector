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

/**
 * Analyze responses from multiple models to determine verdict and confidence
 */
export function analyzeResponses(responses: Record<string, ModelResponse>): ConsensusAnalysis {
  const judgments: Record<string, Classification> = {};
  const policyLimitedResponses: string[] = [];
  const uncertainResponses: string[] = [];

  // Uncertainty patterns that indicate factual uncertainty rather than policy limits
  const uncertaintyPatterns = [
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

  // Extract judgments from each model response
  for (const [model, response] of Object.entries(responses)) {
    if (!response.success || !response.content) {
      continue;
    }

    // Check for explicit opt-outs first
    if (detectRecusal(response.content)) {
      judgments[model] = 'RECUSE';
      continue;
    }

    if (detectPolicyLimitation(response.content)) {
      judgments[model] = 'POLICY_LIMITED';
      policyLimitedResponses.push(model);
      continue;
    }

    const contentUpper = response.content.toUpperCase();
    const contentLower = response.content.toLowerCase();

    // Check for uncertainty indicators
    const uncertain = uncertaintyPatterns.some(pattern => contentLower.includes(pattern));

    // Extract explicit judgments
    if (
      contentUpper.includes('FALSE') &&
      !contentUpper.includes('NOT FALSE') &&
      !contentUpper.includes("ISN'T FALSE")
    ) {
      if (uncertain) {
        judgments[model] = 'UNCERTAIN';
        uncertainResponses.push(model);
      } else {
        judgments[model] = 'FALSE';
      }
    } else if (
      contentUpper.includes('TRUE') &&
      !contentUpper.includes('NOT TRUE') &&
      !contentUpper.includes("ISN'T TRUE")
    ) {
      if (uncertain) {
        judgments[model] = 'UNCERTAIN';
        uncertainResponses.push(model);
      } else {
        judgments[model] = 'TRUE';
      }
    } else if (contentUpper.includes('UNCERTAIN') || uncertain) {
      judgments[model] = 'UNCERTAIN';
      uncertainResponses.push(model);
    } else {
      judgments[model] = 'UNCERTAIN';
      uncertainResponses.push(model);
    }
  }

  // Count different judgments - exclude RECUSE and POLICY_LIMITED
  const substantiveJudgments = Object.fromEntries(
    Object.entries(judgments).filter(([_, v]) => v !== 'RECUSE' && v !== 'POLICY_LIMITED')
  );

  const judgmentCounts = { TRUE: 0, FALSE: 0, UNCERTAIN: 0 };
  for (const judgment of Object.values(substantiveJudgments)) {
    judgmentCounts[judgment as keyof typeof judgmentCounts]++;
  }

  // Determine the majority verdict
  const totalModels = Object.keys(substantiveJudgments).length;
  let majorityVerdict: Classification;

  if (judgmentCounts.UNCERTAIN >= totalModels / 3 || judgmentCounts.UNCERTAIN >= 2) {
    majorityVerdict = 'UNCERTAIN';
  } else {
    // Otherwise use the most common verdict
    majorityVerdict = Object.entries(judgmentCounts).reduce((a, b) =>
      b[1] > a[1] ? b : a
    )[0] as Classification;
  }

  // If there's a tie between TRUE and FALSE, use UNCERTAIN
  if (judgmentCounts.TRUE === judgmentCounts.FALSE && judgmentCounts.TRUE > 0) {
    majorityVerdict = 'UNCERTAIN';
  }

  // Calculate confidence percentage
  let confidence = 0;

  if (totalModels === 0) {
    confidence = 0;
  } else {
    const agreementCount = judgmentCounts[majorityVerdict as keyof typeof judgmentCounts];

    if (majorityVerdict === 'UNCERTAIN') {
      // Cap confidence for UNCERTAIN verdicts
      confidence = Math.min(70, (agreementCount / totalModels) * 100);
    } else {
      // For TRUE/FALSE verdicts
      const policyAligned = policyLimitedResponses.filter(
        model => judgments[model] === majorityVerdict
      ).length;

      const nonPolicyTotal = totalModels - policyLimitedResponses.length;

      if (nonPolicyTotal > 0) {
        // Give more weight to direct, non-policy-limited responses
        const baseConfidence = ((agreementCount - policyAligned) / nonPolicyTotal) * 100;

        // Add bonus for policy-limited responses that still align with majority
        const policyBonus = (policyAligned / totalModels) * 20; // 20% max bonus

        confidence = Math.min(100, baseConfidence + policyBonus);
      } else {
        // If all responses are policy-limited, just use agreement percentage
        confidence = (agreementCount / totalModels) * 90; // Cap at 90% if all are policy-limited
      }

      // Reduce confidence if there are uncertain responses
      if (judgmentCounts.UNCERTAIN > 0) {
        const uncertaintyPenalty = (judgmentCounts.UNCERTAIN / totalModels) * 30;
        confidence = Math.max(40, confidence - uncertaintyPenalty);
      }
    }
  }

  // Determine confidence level text
  let confidenceLevel: ConfidenceLevel;
  if (confidence >= 90) {
    confidenceLevel = 'VERY HIGH';
  } else if (confidence >= 70) {
    confidenceLevel = 'HIGH';
  } else if (confidence >= 50) {
    confidenceLevel = 'MEDIUM';
  } else if (confidence >= 30) {
    confidenceLevel = 'LOW';
  } else {
    confidenceLevel = 'VERY LOW';
  }

  return {
    verdict: majorityVerdict,
    confidence_percentage: Math.round(confidence),
    confidence_level: confidenceLevel,
    model_judgments: judgments,
    policy_limited_responses: policyLimitedResponses,
    uncertain_responses: uncertainResponses,
  };
}
