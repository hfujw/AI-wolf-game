"""
Multi-model configuration example for AI Wolf Game.

Copy this to .env or set environment variables to assign
different LLM providers/models to each player seat.

=== Quick Start ===
Just set LLM_API_KEY, LLM_BASE_URL, LLM_MODEL for all players:
    LLM_API_KEY=your-key
    LLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4/
    LLM_MODEL=GLM-4-Flash

=== Per-Player Config (Advanced) ===
Each player can have a different model using these env vars:
    P{N}_API_KEY  -> Player N's API key
    P{N}_BASE_URL -> Player N's API base URL
    P{N}_MODEL    -> Player N's model name

Example:
    # All players default:
    LLM_API_KEY=sk-default
    LLM_BASE_URL=https://api.openai.com/v1
    LLM_MODEL=gpt-4o-mini

    # Player 1 uses Claude:
    P1_API_KEY=sk-ant-xxx
    P1_BASE_URL=https://api.anthropic.com/v1
    P1_MODEL=claude-3-5-sonnet-20241022

    # Player 3 uses DeepSeek:
    P3_API_KEY=sk-xxx
    P3_BASE_URL=https://api.deepseek.com/v1
    P3_MODEL=deepseek-chat

=== Supported Providers ===
- OpenAI:     https://api.openai.com/v1
- Zhipu AI:   https://open.bigmodel.cn/api/paas/v4/
- DeepSeek:   https://api.deepseek.com/v1
- Anthropic:  https://api.anthropic.com/v1
- Any OpenAI-compatible endpoint
"""
