/**
 * /video/:jobId endpoint handler
 * Returns full HTML result page — handles pending/processing/complete/error states
 */

import type { Env, VideoJob } from '../models/types';

export async function handleVideoResult(jobId: string, env: Env): Promise<Response> {
  const raw = await env.CACHE.get(`video:${jobId}`, 'json');

  if (!raw) {
    return new Response(notFoundPage(), {
      status: 404,
      headers: { 'Content-Type': 'text/html' },
    });
  }

  const job = raw as VideoJob;
  const html = buildPage(jobId, job);

  return new Response(html, {
    headers: { 'Content-Type': 'text/html' },
  });
}

function notFoundPage(): string {
  return wrapPage(
    'Analysis Not Found',
    `
    <div class="text-center py-16">
      <div class="text-6xl mb-6">🔍</div>
      <h2 class="text-2xl font-semibold mb-4">Analysis Not Found</h2>
      <p class="text-gray-400 mb-8">This analysis may have expired or never existed.</p>
      <a href="/" class="inline-block px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition">
        ← Back to Bullshit Detector
      </a>
    </div>
  `
  );
}

function buildPage(jobId: string, job: VideoJob): string {
  if (job.status === 'error') {
    return errorPage(job);
  }

  if (job.status === 'complete' && job.claims && job.overall) {
    return completePage(job);
  }

  // pending / extracting / verifying — show progress UI that polls
  return progressPage(jobId, job);
}

function progressPage(jobId: string, job: VideoJob): string {
  const statusLabel: Record<string, string> = {
    pending: 'Initialising...',
    extracting: 'Watching the video and extracting claims...',
    verifying: `Verifying claims with 5 AI models... (${job.claims_verified ?? 0} / ${job.claims_found ?? '?'})`,
  };

  const label = statusLabel[job.status] ?? 'Processing...';

  const content = `
    <div class="max-w-2xl mx-auto text-center py-16" id="progress-container">
      <div class="loader mx-auto mb-8" style="width:48px;height:48px;border-width:4px;"></div>
      <h2 class="text-2xl font-semibold mb-3" id="status-label">${escapeHtml(label)}</h2>
      <p class="text-gray-400 mb-6" id="progress-detail"></p>

      ${
        job.video_metadata
          ? `
        <div class="card rounded-xl p-6 text-left mb-6">
          <div class="text-xs uppercase tracking-wide text-gray-500 mb-1">Topic</div>
          <p class="font-medium">${escapeHtml(job.video_metadata.primary_topic)}</p>
          ${
            job.video_metadata.summary
              ? `
            <div class="text-xs uppercase tracking-wide text-gray-500 mt-4 mb-1">Summary</div>
            <p class="text-gray-300 text-sm">${escapeHtml(job.video_metadata.summary)}</p>
          `
              : ''
          }
        </div>
      `
          : ''
      }

      <p class="text-gray-500 text-sm">
        Video analysis can take a few minutes. This page updates automatically.
      </p>
    </div>

    <script>
      (function() {
        const jobId = ${JSON.stringify(jobId)};
        const apiBase = window.location.hostname.includes('.pages.dev')
          ? 'https://bullshit-detector.dev-a4b.workers.dev'
          : '';
        let pollTimer = null;

        function poll() {
          fetch(apiBase + '/api/video-status/' + jobId)
            .then(r => r.json())
            .then(data => {
              if (data.status === 'complete' || data.status === 'error') {
                window.location.reload();
                return;
              }

              const labels = {
                pending: 'Initialising...',
                extracting: 'Watching the video and extracting claims...',
                verifying: 'Verifying claims with 5 AI models... (' + (data.claims_verified || 0) + ' / ' + (data.claims_found || '?') + ')',
              };
              const el = document.getElementById('status-label');
              if (el) el.textContent = labels[data.status] || 'Processing...';

              pollTimer = setTimeout(poll, 3000);
            })
            .catch(() => {
              pollTimer = setTimeout(poll, 5000);
            });
        }

        pollTimer = setTimeout(poll, 3000);
      })();
    </script>
  `;

  return wrapPage('Analysing Video — Bullshit Detector', content);
}

function completePage(job: VideoJob): string {
  const overall = job.overall!;
  const claims = job.claims!;

  const scoreColor =
    overall.credibility_score >= 70
      ? '#22c55e'
      : overall.credibility_score >= 40
        ? '#eab308'
        : '#ef4444';

  const scoreLabel =
    overall.credibility_score >= 70
      ? 'Generally Credible'
      : overall.credibility_score >= 40
        ? 'Mixed Credibility'
        : 'Low Credibility';

  const claimsHtml = claims.map(claim => renderClaim(claim)).join('\n');

  const content = `
    <div class="max-w-4xl mx-auto">
      <div class="mb-6">
        <a href="/" class="text-blue-400 hover:text-blue-300 text-sm flex items-center gap-1">
          ← Back to Bullshit Detector
        </a>
      </div>

      <!-- Video header card -->
      <div class="card rounded-xl p-6 shadow-lg mb-6">
        <div class="flex flex-col md:flex-row justify-between items-start gap-4">
          <div class="flex-1">
            <div class="text-xs uppercase tracking-wide text-gray-500 mb-1">Video Analysis</div>
            <h2 class="text-xl font-semibold mb-2">${escapeHtml(job.video_metadata?.primary_topic ?? 'YouTube Video')}</h2>
            ${job.video_metadata?.summary ? `<p class="text-gray-400 text-sm">${escapeHtml(job.video_metadata.summary)}</p>` : ''}
            <a href="${escapeHtml(job.url)}" target="_blank" rel="noopener noreferrer"
               class="inline-block mt-3 text-blue-400 hover:underline text-sm break-all">
              ${escapeHtml(job.url)}
            </a>
          </div>

          <!-- Credibility score -->
          <div class="flex-shrink-0 text-center">
            <div class="text-5xl font-bold mb-1" style="color:${scoreColor}">${overall.credibility_score}%</div>
            <div class="text-sm font-medium" style="color:${scoreColor}">${scoreLabel}</div>
            <div class="mt-3 grid grid-cols-3 gap-2 text-center text-xs">
              <div>
                <div class="text-green-400 font-bold text-lg">${overall.true_count}</div>
                <div class="text-gray-500">True</div>
              </div>
              <div>
                <div class="text-red-400 font-bold text-lg">${overall.false_count}</div>
                <div class="text-gray-500">False</div>
              </div>
              <div>
                <div class="text-yellow-400 font-bold text-lg">${overall.uncertain_count}</div>
                <div class="text-gray-500">Uncertain</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Claims timeline -->
      <h3 class="text-lg font-semibold mb-4 text-gray-300">
        ${claims.length} claim${claims.length !== 1 ? 's' : ''} verified
      </h3>

      <div class="space-y-4 mb-12">
        ${claimsHtml}
      </div>
    </div>
  `;

  return wrapPage(
    `Video Analysis — ${job.video_metadata?.primary_topic ?? 'YouTube Video'} — Bullshit Detector`,
    content
  );
}

function renderClaim(claim: import('../models/types').VideoClaim): string {
  const analysis = claim.analysis;
  const verdict = analysis?.verdict ?? 'UNCERTAIN';

  const verdictColor: Record<string, string> = {
    TRUE: 'bg-green-500',
    FALSE: 'bg-red-500',
    UNCERTAIN: 'bg-yellow-500',
    RECUSE: 'bg-gray-500',
    POLICY_LIMITED: 'bg-gray-500',
  };

  const badgeCls = verdictColor[verdict] ?? 'bg-gray-500';

  const confidencePct = analysis?.confidence_percentage ?? 0;
  const barColor =
    confidencePct >= 70 ? 'truth-high' : confidencePct >= 40 ? 'truth-medium' : 'truth-low';

  const modelResponsesHtml = claim.responses
    ? Object.entries(claim.responses)
        .filter(([, r]) => r.success && r.content)
        .map(
          ([key, r]) => `
          <div class="model-response model-${key} rounded-lg p-3 text-sm">
            <div class="text-xs font-medium text-gray-400 mb-1 uppercase">${escapeHtml(key)}</div>
            <p class="text-gray-300">${escapeHtml(r.content ?? '')}</p>
          </div>
        `
        )
        .join('')
    : '';

  const claimIdAttr = `claim-${escapeHtml(claim.id)}`;

  return `
    <div class="card rounded-xl shadow-lg overflow-hidden">
      <!-- Claim header (always visible) -->
      <button
        class="w-full text-left p-5 flex items-start gap-4 hover:opacity-90 transition focus:outline-none"
        aria-expanded="false"
        aria-controls="detail-${claimIdAttr}"
        onclick="toggleClaim('detail-${claimIdAttr}', this)"
      >
        <!-- Timestamp badge -->
        <div class="flex-shrink-0 mt-0.5">
          <span class="inline-block px-2 py-0.5 rounded bg-gray-700 text-gray-300 text-xs font-mono">
            ${escapeHtml(claim.timestamp)}
          </span>
        </div>

        <!-- Claim text + speaker -->
        <div class="flex-1 min-w-0">
          <p class="font-medium text-sm leading-snug mb-1">${escapeHtml(claim.text)}</p>
          <p class="text-xs text-gray-500">
            ${escapeHtml(claim.speaker)}${claim.context ? ` — ${escapeHtml(claim.context)}` : ''}
          </p>
        </div>

        <!-- Verdict + confidence -->
        <div class="flex-shrink-0 flex flex-col items-end gap-2">
          <span class="px-2 py-0.5 rounded-full text-white text-xs font-semibold ${badgeCls}">
            ${escapeHtml(verdict)}
          </span>
          ${
            analysis
              ? `
            <div class="w-20">
              <div class="confidence-bar">
                <div class="confidence-level ${barColor}" style="width:${confidencePct}%"></div>
              </div>
              <div class="text-xs text-gray-500 text-right mt-0.5">${escapeHtml(analysis.confidence_level ?? '')} confidence</div>
            </div>
          `
              : ''
          }
        </div>
      </button>

      <!-- Expandable model responses -->
      <div id="detail-${claimIdAttr}" class="hidden border-t border-gray-700 p-4 space-y-3">
        ${modelResponsesHtml || '<p class="text-gray-500 text-sm">No model responses available.</p>'}
      </div>
    </div>
  `;
}

function errorPage(job: VideoJob): string {
  const content = `
    <div class="max-w-2xl mx-auto text-center py-16">
      <div class="text-6xl mb-6">⚠️</div>
      <h2 class="text-2xl font-semibold mb-4">Analysis Failed</h2>
      <p class="text-gray-400 mb-8">${escapeHtml(job.error ?? 'An unknown error occurred.')}</p>
      <a href="/" class="inline-block px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition">
        ← Try Another Video
      </a>
    </div>
  `;
  return wrapPage('Analysis Failed — Bullshit Detector', content);
}

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function wrapPage(title: string, bodyContent: string): string {
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${title}</title>
  <link href="https://cdnjs.cloudflare.com/ajax/libs/tailwindcss/2.2.19/tailwind.min.css" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
  <style>
    @import url('https://fonts.bunny.net/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    :root {
      --bg-primary: #0f172a;
      --bg-secondary: #1e293b;
      --text-primary: #e2e8f0;
      --text-secondary: #94a3b8;
      --accent-primary: #3b82f6;
      --card-bg: rgba(30, 41, 59, 0.8);
      --card-border: rgba(255, 255, 255, 0.1);
      --model-bg: rgba(15, 23, 42, 0.7);
    }

    body {
      font-family: 'Inter', sans-serif;
      background-color: var(--bg-primary);
      color: var(--text-primary);
    }

    .card {
      background: var(--card-bg);
      backdrop-filter: blur(10px);
      border: 1px solid var(--card-border);
    }

    .loader {
      border: 3px solid rgba(255, 255, 255, 0.1);
      border-radius: 50%;
      border-top: 3px solid var(--accent-primary);
      width: 24px;
      height: 24px;
      animation: spin 1s linear infinite;
    }

    @keyframes spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }

    .confidence-bar {
      height: 6px;
      background: var(--bg-secondary);
      border-radius: 4px;
      overflow: hidden;
    }

    .confidence-level {
      height: 100%;
      border-radius: 4px;
    }

    .truth-high { background: linear-gradient(90deg, #22c55e, #16a34a); }
    .truth-medium { background: linear-gradient(90deg, #eab308, #ca8a04); }
    .truth-low { background: linear-gradient(90deg, #ef4444, #dc2626); }

    .model-response {
      border-left: 4px solid transparent;
      background-color: var(--model-bg);
    }

    .model-openai { border-left-color: #10b981; }
    .model-anthropic { border-left-color: #8b5cf6; }
    .model-mistral { border-left-color: #3b82f6; }
    .model-deepseek { border-left-color: #f59e0b; }
    .model-gemini { border-left-color: #ef4444; }

    .gradient-text {
      background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
      -webkit-background-clip: text;
      background-clip: text;
      color: transparent;
    }
  </style>
</head>
<body class="min-h-screen">
  <div class="max-w-5xl mx-auto px-4 py-8">
    <header class="mb-8 flex items-center gap-4">
      <a href="/" class="text-2xl font-bold gradient-text hover:opacity-80 transition">
        Bullshit Detector
      </a>
      <span class="text-gray-600">/ Video Analysis</span>
    </header>

    ${bodyContent}
  </div>

  <script>
    function toggleClaim(detailId, btn) {
      const detail = document.getElementById(detailId);
      if (!detail) return;
      const isOpen = !detail.classList.contains('hidden');
      detail.classList.toggle('hidden', isOpen);
      btn.setAttribute('aria-expanded', String(!isOpen));
    }
  </script>
</body>
</html>`;
}
