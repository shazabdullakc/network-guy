"""LLM abstraction layer — supports multiple providers.

Supported providers:
  - deepseek   (default, best free reasoning, OpenAI-compatible)
  - gemini     (Google, generous free tier)
  - openrouter (aggregator, access to many models)
  - grok       (xAI, OpenAI-compatible)
  - anthropic  (Claude, best quality, paid)

All OpenAI-compatible providers (deepseek, openrouter, grok) share the same
integration code — just different base_url and model name.

Usage:
  Set environment variables:
    DEEPSEEK_API_KEY=sk-...
    GEMINI_API_KEY=AIza...
    OPENROUTER_API_KEY=sk-or-...
    GROK_API_KEY=xai-...
    ANTHROPIC_API_KEY=sk-ant-...

  The system auto-detects which key is available and uses that provider.
  Priority order: deepseek > gemini > openrouter > grok > anthropic
"""

from __future__ import annotations

import os

# Provider configurations
PROVIDERS = {
    "deepseek": {
        "env_key": "DEEPSEEK_API_KEY",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
        "type": "openai_compatible",
    },
    "gemini": {
        "env_key": "GEMINI_API_KEY",
        "base_url": None,  # Uses google SDK
        "model": "gemini-2.5-flash",
        "type": "gemini",
    },
    "openrouter": {
        "env_key": "OPENROUTER_API_KEY",
        "base_url": "https://openrouter.ai/api/v1",
        "model": "deepseek/deepseek-chat-v3-0324:free",
        "type": "openai_compatible",
    },
    "grok": {
        "env_key": "GROK_API_KEY",
        "base_url": "https://api.x.ai/v1",
        "model": "grok-3-mini",
        "type": "openai_compatible",
    },
    "anthropic": {
        "env_key": "ANTHROPIC_API_KEY",
        "base_url": None,
        "model": "claude-sonnet-4-20250514",
        "type": "anthropic",
    },
}

# Priority order for auto-detection
PRIORITY = ["deepseek", "gemini", "openrouter", "grok", "anthropic"]


def detect_provider() -> tuple[str, str] | None:
    """Auto-detect which LLM provider has an API key set.

    Returns (provider_name, api_key) or None if no key found.
    """
    for provider_name in PRIORITY:
        config = PROVIDERS[provider_name]
        api_key = os.environ.get(config["env_key"], "")
        if api_key:
            return provider_name, api_key
    return None


def call_llm(system_prompt: str, user_prompt: str, provider: str | None = None) -> str:
    """Call the LLM with system + user prompts.

    Args:
        system_prompt: System instructions (RCA format rules)
        user_prompt: User query + agent findings
        provider: Force a specific provider. None = auto-detect.

    Returns:
        LLM response text.
    """
    # Detect provider
    if provider:
        config = PROVIDERS.get(provider)
        if not config:
            return f"Unknown provider: {provider}"
        api_key = os.environ.get(config["env_key"], "")
        if not api_key:
            return f"No API key found for {provider}. Set {config['env_key']} environment variable."
    else:
        detected = detect_provider()
        if not detected:
            return _no_api_key_fallback(user_prompt)
        provider, api_key = detected
        config = PROVIDERS[provider]

    # Route to the right integration
    try:
        if config["type"] == "openai_compatible":
            return _call_openai_compatible(
                api_key=api_key,
                base_url=config["base_url"],
                model=config["model"],
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                provider_name=provider,
            )
        elif config["type"] == "gemini":
            return _call_gemini(
                api_key=api_key,
                model=config["model"],
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
        elif config["type"] == "anthropic":
            return _call_anthropic(
                api_key=api_key,
                model=config["model"],
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
        else:
            return f"Unsupported provider type: {config['type']}"
    except Exception as e:
        return f"LLM call failed ({provider}): {e}\n\n{_no_api_key_fallback(user_prompt)}"


def _call_openai_compatible(
    api_key: str,
    base_url: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    provider_name: str = "",
) -> str:
    """Call any OpenAI-compatible API (DeepSeek, OpenRouter, Grok)."""
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=2000,
        temperature=0.3,
    )

    return response.choices[0].message.content


def _call_gemini(
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
) -> str:
    """Call Google Gemini API."""
    from google import genai

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=model,
        contents=f"{system_prompt}\n\n{user_prompt}",
        config={
            "max_output_tokens": 2000,
            "temperature": 0.3,
        },
    )

    return response.text


def _call_anthropic(
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
) -> str:
    """Call Anthropic Claude API."""
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model=model,
        max_tokens=2000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    return message.content[0].text


def _no_api_key_fallback(user_prompt: str) -> str:
    """When no API key is available, show raw findings."""
    return (
        "*No LLM API key detected. Set one of these environment variables:*\n"
        "- `DEEPSEEK_API_KEY` (recommended, free 50M tokens)\n"
        "- `GEMINI_API_KEY` (free 1M tokens/day)\n"
        "- `OPENROUTER_API_KEY` (free models available)\n"
        "- `GROK_API_KEY` (free tier)\n"
        "- `ANTHROPIC_API_KEY` (paid)\n\n"
        "**Raw Agent Findings Below:**\n\n"
        + user_prompt
    )


def get_provider_info() -> dict:
    """Get info about which provider is active."""
    detected = detect_provider()
    if not detected:
        return {"active": False, "provider": None, "model": None}

    provider_name, _ = detected
    config = PROVIDERS[provider_name]
    return {
        "active": True,
        "provider": provider_name,
        "model": config["model"],
        "type": config["type"],
    }
