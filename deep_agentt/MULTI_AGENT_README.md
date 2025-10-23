# Multi-Agent Testing System

A complete multi-agent system using **deepagents** and **LangChain** for generating comprehensive test scenarios from user stories and project context.

## 📋 System Architecture

### Overview
```
┌─────────────────────────────────────────────────────────┐
│              MAIN AGENT (Orchestrator)                  │
│   - Receives user story & project context               │
│   - Assesses complexity level                           │
│   - Coordinates 3 specialist sub-agents                 │
└────────────────┬────────────────────────────────────────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
    ▼            ▼            ▼
┌─────────┐  ┌────────────┐  ┌──────────────┐
│   E2E   │  │Integration │  │  Functional  │
│ Test    │  │   Test     │  │     Test     │
│ Agent   │  │   Agent    │  │    Agent     │
└─────────┘  └────────────┘  └──────────────┘
    │            │                  │
    └────────────┼──────────────────┘
                 │
    ┌────────────▼────────────┐
    │  Aggregated Test        │
    │  Scenarios              │
    └─────────────────────────┘
```

### Components

#### 1. **Main Agent (Orchestrator)**
- **Role**: Orchestrates all sub-agents
- **Responsibilities**:
  - Receives user story and project context
  - Assesses complexity level (low, medium, high, critical)
  - Delegates work to specialist agents
  - Ensures comprehensive coverage based on complexity
- **Complexity Handling**:
  - **Low**: Basic happy path testing
  - **Medium**: Multiple paths, some edge cases
  - **High**: Complex interactions, critical paths
  - **Critical**: Business-critical, security-sensitive tests

#### 2. **Sub-Agent 1: E2E Test Specialist**
- **Focus**: End-to-End user journeys
- **Generates**:
  - Complete workflow test scenarios
  - User journey flows
  - Critical user paths
  - Success criteria for each scenario

#### 3. **Sub-Agent 2: Integration Test Specialist**
- **Focus**: System integration and service communication
- **Generates**:
  - API integration test cases
  - Database interaction tests
  - Service-to-service communication tests
  - Data consistency validation tests

#### 4. **Sub-Agent 3: Functional Test Specialist**
- **Focus**: Individual feature functionality
- **Generates**:
  - Core feature tests
  - Edge case and boundary tests
  - Input validation tests
  - Error handling scenarios

---

## 🚀 Setup & Installation

### Prerequisites
- Python 3.11+
- Virtual environment (`.venv`)
- OpenAI API Key

### Step 1: Activate Virtual Environment
```bash
cd /home/suyodhan/Desktop/POC/noobPractice
source .venv/bin/activate
```

### Step 2: Install Required Dependencies
```bash
# Using uv (recommended)
uv add deepagents langchain-core

# Or using pip
pip install deepagents langchain-core
```

### Step 3: Verify Current Dependencies
```bash
# Check pyproject.toml
cat pyproject.toml

# Current dependencies:
# - dotenv>=0.9.9
# - faiss-cpu>=1.12.0
# - fastapi>=0.119.1
# - langchain>=1.0.0
# - langchain-openai>=1.0.0
# - notebook>=7.4.7
# - openai>=2.5.0
# - uvicorn>=0.38.0
# - deepagents (newly added)
# - langchain-core (newly added)
```

### Step 4: Set Environment Variables
```bash
# Create .env file (if not exists)
export OPENAI_API_KEY="your_openai_api_key"
```

---

## 📝 Usage

### Run the Multi-Agent System
```bash
python multi_agent_testing_system.py
```

### Example Input
```python
USER_STORY = """
As an e-commerce customer, I want to search for products by multiple criteria
(category, price range, brand, ratings), apply real-time filters, and sort 
results by price, popularity, or newest so that I can quickly find products 
that match my needs. The search should be fast (< 1 second response time), 
handle special characters, support pagination, and remember my last search.
"""

PROJECT_CONTEXT = """
Platform: E-Commerce Marketplace
Tech Stack: React (Frontend), Node.js/Express (Backend), PostgreSQL (DB), Elasticsearch (Search)
Scale: 100K+ active users, 1M+ products in catalog
Performance SLA: Page load < 2 seconds, Search results < 1 second
Third-party: Stripe (Payment), SendGrid (Email), Cloudflare (CDN)
Database: PostgreSQL with read replicas, Redis cache layer
"""

# Complexity levels: "low", "medium", "high", "critical"
complexity = "high"
```

### Expected Output
```
================================================================================
                    MULTI-AGENT TESTING SYSTEM
================================================================================

================================================================================
PART 2: MULTI-AGENT SYSTEM (Using deepagents)
================================================================================

[ORCHESTRATION] Creating multi-agent system...
✅ Multi-agent system created

[MAIN AGENT] Processing request and orchestrating sub-agents...
Complexity Level: HIGH

[SUB-AGENT 1] E2E Test Specialist - Generating scenarios...
✅ E2E scenarios generated

[SUB-AGENT 2] Integration Test Specialist - Generating scenarios...
✅ Integration scenarios generated

[SUB-AGENT 3] Functional Test Specialist - Generating scenarios...
✅ Functional scenarios generated

================================================================================
🎯 FINAL TEST SCENARIOS - AGGREGATED FROM ALL SUB-AGENTS
================================================================================

────────────────────────────────────────────────────────────────────────────────
📌 E2E TEST SCENARIOS
────────────────────────────────────────────────────────────────────────────────
[Test scenarios from E2E specialist...]

────────────────────────────────────────────────────────────────────────────────
🔗 INTEGRATION TEST SCENARIOS
────────────────────────────────────────────────────────────────────────────────
[Test scenarios from Integration specialist...]

────────────────────────────────────────────────────────────────────────────────
⚙️  FUNCTIONAL TEST SCENARIOS
────────────────────────────────────────────────────────────────────────────────
[Test scenarios from Functional specialist...]
```

---

## 🔧 Key Functions

### `create_multi_agent_system()`
Creates the complete multi-agent system using deepagents infrastructure.

**Returns**: A `create_deep_agent` instance with 3 sub-agents configured.

### `run_multi_agent_system(user_story, project_context, complexity)`
Orchestrates the multi-agent system execution.

**Parameters**:
- `user_story` (str): The user story to analyze
- `project_context` (str): Project technical context
- `complexity` (str): Complexity level (low/medium/high/critical)

**Returns**: Dictionary with test scenarios from all agents

### `run_fallback_multi_agent_system(user_story, project_context, complexity)`
Fallback implementation that calls sub-agents directly without deepagents infrastructure.

Used if deepagents setup fails.

### `display_results(results)`
Formats and displays the aggregated test scenarios from all agents.

---

## 🏗️ Deepagents Structure

### SubAgentMiddleware Configuration
```python
subagents = [
    {
        "name": "e2e_test_specialist",
        "description": "Generates E2E test scenarios",
        "system_prompt": E2E_SYSTEM_PROMPT,
        "tools": [],  # No tools - pure LLM analysis
        "model": e2e_model,
    },
    {
        "name": "integration_test_specialist",
        "description": "Generates integration test scenarios",
        "system_prompt": INTEGRATION_SYSTEM_PROMPT,
        "tools": [],
        "model": integration_model,
    },
    {
        "name": "functional_test_specialist",
        "description": "Generates functional test scenarios",
        "system_prompt": FUNCTIONAL_SYSTEM_PROMPT,
        "tools": [],
        "model": functional_model,
    }
]

agent = create_deep_agent(
    model=main_model,
    system_prompt=MAIN_AGENT_SYSTEM_PROMPT,
    tools=[],
    subagents=subagents,
)
```

---

## 📊 Complexity-Based Test Generation

### Low Complexity
- Basic happy path testing
- Single user flow
- Standard expected outcomes

### Medium Complexity
- Multiple user paths
- Some edge cases
- Standard integration points

### High Complexity
- Complex feature interactions
- Multiple critical paths
- Extensive edge case coverage
- Integration with multiple services

### Critical Complexity
- Business-critical scenarios
- Security-sensitive paths
- Performance-critical tests
- Data consistency validation
- All edge cases and error scenarios

---

## 🛠️ Customization

### Add a New Sub-Agent
```python
def create_multi_agent_system():
    # Create new agent model
    new_model = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
    
    # Add to subagents list
    subagents.append({
        "name": "performance_test_specialist",
        "description": "Generates performance test scenarios",
        "system_prompt": PERFORMANCE_SYSTEM_PROMPT,
        "tools": [],
        "model": new_model,
    })
```

### Modify System Prompts
Edit the system prompt constants:
- `E2E_SYSTEM_PROMPT`
- `INTEGRATION_SYSTEM_PROMPT`
- `FUNCTIONAL_SYSTEM_PROMPT`
- `MAIN_AGENT_SYSTEM_PROMPT`

### Change Model
```python
# Use different LLM
model = ChatOpenAI(
    model="gpt-4-turbo",  # Change model
    temperature=0.5,      # Adjust temperature
    max_tokens=2000       # Set token limit
)
```

---

## 📚 Dependencies Summary

| Package | Version | Purpose |
|---------|---------|---------|
| `deepagents` | Latest | Multi-agent orchestration |
| `langchain-core` | >=0.1.0 | LangChain core functionality |
| `langchain-openai` | >=1.0.0 | OpenAI integration |
| `langchain` | >=1.0.0 | Main LangChain framework |
| `openai` | >=2.5.0 | OpenAI API client |
| `dotenv` | >=0.9.9 | Environment variable management |

---

## 🐛 Troubleshooting

### Issue: `ModuleNotFoundError: No module named 'deepagents'`
**Solution**: Run `uv add deepagents` or `pip install deepagents`

### Issue: `OPENAI_API_KEY not found`
**Solution**: Set environment variable
```bash
export OPENAI_API_KEY="your_key_here"
```

### Issue: Deepagents infrastructure error
**Solution**: System automatically falls back to direct sub-agent calls

---

## 📖 References

- [deepagents GitHub](https://github.com/langchain-ai/deepagents)
- [LangChain Documentation](https://python.langchain.com/)
- [LangChain API Reference](https://reference.langchain.com/python/)

---

## ✅ System Status

✓ Single Agent functions (available but not executed)  
✓ Multi-Agent System with 3 Specialists  
✓ Deepagents Integration  
✓ Fallback Sub-Agent Calls  
✓ Complexity-Based Test Generation  
✓ Full Aggregation Pipeline  

---

**Last Updated**: October 2025  
**Version**: 1.0.0
