---
name: user_api_keys
description: User has free LLM API keys (Gemini, OpenRouter, Grok, DeepSeek) but NOT Anthropic. System designed to auto-detect available provider.
type: user
---

User has access to these free LLM APIs: Gemini, OpenRouter, Grok, DeepSeek.
Does NOT have an Anthropic API key.
Preference: use free providers during development, move to Anthropic later.
We built a multi-provider LLM layer that auto-detects which key is available.
