# Bullshit Detector

A privacy-first misinformation detection tool that leverages consensus across multiple AI models to evaluate claims and provide confidence-scored verdicts.

![Bullshit Detector](https://img.shields.io/badge/status-active-brightgreen)
![Python](https://img.shields.io/badge/python-3.8+-blue)
![Flask](https://img.shields.io/badge/flask-2.0+-blue)

## Overview

The Bullshit Detector addresses the modern evolution of Brandolini's Law - where creating misinformation remains cheap, but verification now requires significant computational resources. By querying multiple AI models and analyzing their consensus, we provide rapid, transparent fact-checking with appropriate epistemic humility.

### Key Features

- **Multi-model consensus**: Queries GPT-4o, Claude 3, Mistral, and DeepSeek for diverse perspectives
- **Privacy-first**: No request logging or user tracking
- **Confidence scoring**: Transparent uncertainty communication rather than false certainty  
- **Policy-aware**: Distinguishes between factual uncertainty and model policy limitations
- **Real-time analysis**: Rapid verification with detailed reasoning from each model

## How It Works

1. **Input Processing**: Claims are preprocessed to remove bias and standardize language
2. **Multi-model Querying**: Each AI model independently evaluates the claim
3. **Consensus Analysis**: Responses are analyzed for explicit and implicit judgments
4. **Confidence Calculation**: Agreement levels determine verdict confidence
5. **Transparent Results**: Full model responses shown with clear verdict and confidence level

### Verdict Types

- **TRUE**: Claim supported by evidence and model consensus
- **FALSE**: Claim contradicted by evidence and model consensus  
- **UNCERTAIN**: Insufficient evidence or significant model disagreement
- **RECUSE**: Unanswerable due to paradox or philosophical objection
- **POLICY_LIMITED**: Model declined to evaluate due to safety constraints

### Confidence Levels

- **VERY HIGH (90-100%)**: Near-unanimous agreement
- **HIGH (70-89%)**: Strong consensus with minimal uncertainty
- **MEDIUM (50-69%)**: Majority agreement with notable disagreement
- **LOW (30-49%)**: Weak consensus with substantial uncertainty
- **VERY LOW (<30%)**: No clear consensus or predominantly uncertain

## Technical Architecture

### Backend
- **Cloudflare Workers** (TypeScript) with RESTful API
- **Multi-provider AI integration** (OpenAI, Anthropic, Mistral, DeepSeek)
- **Cron Triggers** for scheduled model metadata updates
- **Workers KV** for persistent edge storage

### Frontend
- **Cloudflare Pages** serving static HTML
- **Responsive design** with dark/light mode support
- **Real-time results** with animated loading states
- **Tailwind CSS** for modern styling

### Key Files
- `src/worker.ts` - Main Workers entry point and API endpoints
- `src/utils/preprocess.ts` - Query preprocessing and normalization
- `src/scheduled/discovery.ts` - Background model metadata collection
- `public/index.html` - Frontend interface

## Deployment

See [DEPLOY.md](DEPLOY.md) for Cloudflare deployment instructions.

## API Usage

### Evaluate a Claim
```bash
curl -X POST https://bullshitdetector.ai/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "The moon landing was faked"}'
```

### Response Format
```json
{
  "query": "The moon landing was faked",
  "structured_query": "You are part of the Bullshit Detector...",
  "responses": {
    "gpt-4o": {"success": true, "content": "FALSE. The moon landing...", "model": "gpt-4o"},
    "claude-3": {"success": true, "content": "FALSE. The Apollo missions...", "model": "claude-3"},
    "mistral": {"success": true, "content": "FALSE. There is overwhelming...", "model": "mistral"},
    "deepseek": {"success": true, "content": "FALSE. The evidence for...", "model": "deepseek"}
  },
  "analysis": {
    "verdict": "FALSE",
    "confidence_percentage": 95,
    "confidence_level": "VERY HIGH",
    "model_judgments": {"gpt-4o": "FALSE", "claude-3": "FALSE", "mistral": "FALSE", "deepseek": "FALSE"}
  }
}
```

## Methodology

The Bullshit Detector implements a sophisticated consensus algorithm that:

1. **Preprocesses queries** to remove leading bias and standardize language
2. **Extracts explicit judgments** (TRUE/FALSE/UNCERTAIN) from model responses
3. **Identifies policy limitations** vs. genuine factual uncertainty
4. **Calculates confidence** based on agreement levels and uncertainty patterns
5. **Handles edge cases** like ties, contradictions, and recusals appropriately

See the [whitepaper](Bullshit%20Detector%20Whitepaper.txt) for detailed methodology and examples.

## Limitations

- Dependent on external AI API availability and costs
- Training data cutoffs may affect recent event evaluation
- Environmental impact of multiple model queries
- Preprocessing may struggle with intentionally obfuscated claims
- Cannot determine absolute truth, only model consensus

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Roadmap

- [ ] Enhanced preprocessing with semantic analysis
- [ ] Adversarial prompt detection
- [ ] Citation retrieval for model claims
- [ ] Domain-specific confidence algorithms
- [ ] Non-Western model integration
- [ ] Optional user accounts for verification history

## Support

The Bullshit Detector is free to use. If you find it valuable, consider [supporting the project](https://bullshitdetector.ai/) to help cover API costs and infrastructure.

## License

This project is open source. See the repository for license details.

---

*"In an era of rampant misinformation, tools that help users quickly assess claims while maintaining appropriate epistemic humility are invaluable."*