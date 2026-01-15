# Plan: Add Google Gemini to Bullshit Detector

Original lives at /Users/zielinski/.claude/plans/squishy-wandering-clarke.md

## Overview

Add Google Gemini (gemini-2.0-flash-exp) as a 5th AI model to the Bullshit Detector consensus system.

## Model Selection

- **Model ID**: `gemini-2.0-flash-exp`
- **Display Name**: "Gemini 2.0 Flash"
- **API Endpoint**: `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent`
- **Docs URL**: `https://ai.google.dev/gemini-api/docs`

## Implementation Steps

### 1. Update Type Definitions

**File**: `src/models/types.ts`

- Add `gemini: ModelConfig` to `FullModelConfig` interface
- Add `GEMINI_API_KEY: string` to `Env` interface

### 2. Update Fallback Configuration

**File**: `src/models/config.ts`

- Add gemini entry to `FALLBACK_CONFIG`:

```typescript
gemini: {
  id: 'gemini-2.0-flash-exp',
  display_name: 'Gemini 2.0 Flash',
  docs_url: 'https://ai.google.dev/gemini-api/docs',
}
```

**File**: `src/fallback/model_config.json`

- Add same gemini entry to JSON fallback

### 3. Implement Gemini Query Function

**File**: `src/models/query.ts`

Add new function following this pattern:

```typescript
async function queryGemini(prompt: string, env: Env): Promise<ModelResponse> {
  // Endpoint: https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent
  // API key goes in URL query param: ?key=...
  // Request body format:
  {
    contents: [
      {
        parts: [{ text: prompt }],
      },
    ];
  }
  // Response path: ['candidates', 0, 'content', 'parts', 0, 'text']
}
```

Key differences from other providers:

- API key goes in URL query parameter, not header
- Request format: `contents` array with `parts`
- Response format: `candidates[0].content.parts[0].text`
- 30s timeout like other models
- max_tokens equivalent might be `maxOutputTokens` in generation config

### 4. Add to Parallel Execution

**File**: `src/models/query.ts`

- Add `queryGemini(prompt, env)` to the `Promise.all()` array in `queryAllModels()`
- Add to return object: `gemini: geminiResponse`
- Update destructuring to include gemini response

### 5. Add Model Discovery for Gemini

**File**: `src/scheduled/discovery.ts`

- Add Gemini to `discoverAllModels()` function
- Endpoint: `https://generativelanguage.googleapis.com/v1beta/models`
- API key in query param: `?key=${env.GEMINI_API_KEY}`
- Filter for models starting with `gemini-`
- Sort by newest creation date
- Extract display_name from response

### 6. Update Frontend UI

**File**: `public/index.html`

**Add HTML container** (after deepseek container):

```html
<div id="gemini-container" class="model-response model-gemini rounded-lg p-4 hidden">
  <div class="flex items-center mb-3">
    <div class="w-8 h-8 rounded-full bg-gradient-to-r from-red-400 to-orange-500">
      <i class="fas fa-robot text-white"></i>
    </div>
    <span class="flag-emoji">🇺🇸</span>
    <h3 class="font-medium" id="gemini-model-name">Gemini 2.0</h3>
    <div class="text-xs text-gray-400">Google</div>
  </div>
  <p id="gemini-response" class="text-gray-300"></p>
</div>
```

**Add CSS styling**:

```css
.model-gemini {
  border-left: 4px solid;
  border-left-color: #ef4444; /* Red to match other vibrant colors */
}
```

**Add JavaScript variables**:

- `const geminiContainer = document.getElementById('gemini-container');`
- `const geminiResponse = document.getElementById('gemini-response');`
- `const geminiModelName = document.getElementById('gemini-model-name');`

**Update response display logic**:

```javascript
if (data.responses['gemini'] && data.responses['gemini'].success) {
  geminiContainer.classList.remove('hidden');
  geminiResponse.textContent = data.responses['gemini'].content;
}
```

**Add to niceNames mapping**:

```javascript
const niceNames = {
  openai: 'GPT-5',
  anthropic: 'Claude Haiku',
  mistral: 'Mistral Medium',
  deepseek: 'DeepSeek',
  gemini: 'Gemini 2.0',
};
```

### 7. Set Environment Secret

**Action**: Run command to set API key

```bash
echo "AIzaSyA5gEt5f8GKDqaLSvqZFc5n5Mnv-ytoy78" | wrangler secret put GEMINI_API_KEY
```

### 8. Deploy Updates

**Actions**:

1. Deploy Worker: `wrangler deploy`
2. Deploy Pages: `wrangler pages deploy public --project-name=bullshit-detector --branch=main`
3. Test with a query to verify all 5 models respond

### 9. Update Documentation

**File**: `wrangler.toml` (comments section)

- Add `GEMINI_API_KEY` to the list of required secrets

**File**: `deploy.md` (if updating)

- Add Gemini API key to Step 2 secret setup instructions

## Critical Files to Modify

1. `src/models/types.ts` - Type definitions
2. `src/models/config.ts` - Fallback config
3. `src/fallback/model_config.json` - JSON fallback
4. `src/models/query.ts` - Query implementation
5. `src/scheduled/discovery.ts` - Model discovery
6. `public/index.html` - Frontend UI
7. `wrangler.toml` - Documentation (comments only)

## Testing Checklist

- [ ] All 5 models return responses (or appropriate errors)
- [ ] Gemini container appears in UI when successful
- [ ] Gemini response is properly formatted (markdown stripped)
- [ ] Consensus analysis includes Gemini verdict
- [ ] Model metadata endpoint returns Gemini info
- [ ] Cron job discovers Gemini models successfully

## Notes

- Gemini API is different from other providers - uses query params for auth and different request/response format
- Free tier available for gemini-2.0-flash-exp
- Consider that with 5 models, consensus will be even more robust
- OpenAI still rate-limited, so system will work with 4/5 models (Claude, Mistral, DeepSeek, Gemini)
