# OpenRouter Integration Setup Guide

## 🚀 Quick Start

### 1. Install Dependencies
```bash
uv add openrouter
```

### 2. Get OpenRouter API Key
1. Visit [OpenRouter.ai](https://openrouter.ai/)
2. Sign up for an account
3. Get your API key from the dashboard

### 3. Set Environment Variables
```bash
# Add to your .env file
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Fallback providers (optional)
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

### 4. Run the System
```bash
uv run multi_agent_testing_system.py
```

## 🔧 Configuration

### Model Selection
You can customize which models each agent uses by modifying `OPENROUTER_MODELS` in the code:

```python
OPENROUTER_MODELS = {
    "main_agent": "openai/gpt-4o-mini",           # Main orchestrator
    "e2e_specialist": "anthropic/claude-3-5-haiku-20241022",  # E2E testing
    "integration_specialist": "openai/gpt-4o-mini",           # Integration testing  
    "functional_specialist": "meta-llama/llama-3.1-8b-instruct:free",  # Functional testing
}
```

### Available Models on OpenRouter
- **OpenAI**: `openai/gpt-4o`, `openai/gpt-4o-mini`, `openai/gpt-3.5-turbo`
- **Anthropic**: `anthropic/claude-3-5-sonnet-20241022`, `anthropic/claude-3-5-haiku-20241022`
- **Meta**: `meta-llama/llama-3.1-8b-instruct:free`, `meta-llama/llama-3.1-70b-instruct`
- **Google**: `google/gemini-pro`, `google/gemini-flash-1.5`
- **And many more!**

## 💡 Benefits of OpenRouter

### 1. **Unified API**
- Single API for multiple LLM providers
- No need to manage multiple API keys
- Consistent interface across providers

### 2. **Cost Optimization**
- Automatic model selection based on cost
- Fallback mechanisms for high-traffic periods
- Usage tracking and analytics

### 3. **Easy Model Switching**
- Change models without code changes
- A/B testing different models
- Quick experimentation

### 4. **Reliability**
- Automatic failover between providers
- Load balancing
- High availability

## 🔄 How It Works

### 1. **Model Factory Pattern**
```python
def create_model(agent_type: str, temperature: float = 0.7):
    if OPENROUTER_AVAILABLE and os.getenv("OPENROUTER_API_KEY"):
        # Use OpenRouter with specific model
        return OpenRouterModel(client, model_name, temperature)
    else:
        # Fallback to direct providers
        return init_chat_model(fallback_model, temperature=temperature)
```

### 2. **Agent-Specific Models**
- **Main Agent**: Uses orchestrator-optimized model
- **E2E Specialist**: Uses reasoning-focused model
- **Integration Specialist**: Uses technical model
- **Functional Specialist**: Uses cost-effective model

### 3. **Automatic Fallback**
- If OpenRouter is unavailable, falls back to direct providers
- If specific model fails, can fallback to alternative models
- Graceful degradation ensures system always works

## 🛠️ Troubleshooting

### Common Issues

1. **"OpenRouter not available"**
   - Install: `uv add openrouter`
   - Check import: `from openrouter import OpenRouter`

2. **"API key not found"**
   - Set environment variable: `export OPENROUTER_API_KEY=your_key`
   - Check .env file: `OPENROUTER_API_KEY=your_key`

3. **"Model not found"**
   - Check model name in OpenRouter dashboard
   - Verify model is available and accessible
   - Try alternative model names

4. **"Rate limit exceeded"**
   - OpenRouter handles rate limiting automatically
   - Consider upgrading your OpenRouter plan
   - Use fallback models for high-volume usage

### Debug Mode
Enable debug logging to see which models are being used:

```python
# The system automatically prints model usage
🔗 Using OpenRouter model: openai/gpt-4o-mini for main_agent
🔄 Using fallback model: openai:gpt-4o-mini for e2e_specialist
```

## 📊 Usage Examples

### Basic Usage
```python
# System automatically detects and uses OpenRouter
results = run_multi_agent_system(USER_STORY, PROJECT_CONTEXT, complexity="high")
```

### Custom Model Configuration
```python
# Modify OPENROUTER_MODELS to use different models
OPENROUTER_MODELS = {
    "main_agent": "anthropic/claude-3-5-sonnet-20241022",
    "e2e_specialist": "openai/gpt-4o",
    "integration_specialist": "meta-llama/llama-3.1-70b-instruct",
    "functional_specialist": "google/gemini-pro",
}
```

### Fallback Testing
```python
# Test fallback by removing OpenRouter API key
unset OPENROUTER_API_KEY
# System will automatically use direct providers
```

## 🎯 Best Practices

1. **Start with Free Models**: Use free models for testing
2. **Monitor Usage**: Check OpenRouter dashboard for usage patterns
3. **Optimize Costs**: Use cheaper models for simple tasks
4. **Test Fallbacks**: Ensure system works without OpenRouter
5. **Model Selection**: Choose models based on task complexity

## 🔗 Resources

- [OpenRouter Documentation](https://openrouter.ai/docs)
- [Available Models](https://openrouter.ai/models)
- [API Reference](https://openrouter.ai/docs/api)
- [Pricing](https://openrouter.ai/pricing)
