# DeepAgents Internal Architecture & Flow

## 🏗️ Complete System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER REQUEST                                     │
│   "Generate test scenarios for e-commerce search feature"               │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      MAIN ORCHESTRATOR AGENT                             │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  Model: gpt-4o-mini (PRIMARY)                                     │  │
│  │  System Prompt: Main Agent Instructions                           │  │
│  │  Tools: write_todos, plan, task()                                 │  │
│  │  Middleware: [ModelFallbackMiddleware]                            │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  Role: Assess complexity, create plan, delegate to sub-agents           │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
        ▼                        ▼                        ▼
┌───────────────┐      ┌──────────────────┐      ┌──────────────────┐
│  SUB-AGENT 1  │      │   SUB-AGENT 2    │      │   SUB-AGENT 3    │
│               │      │                  │      │                  │
│  E2E Test     │      │  Integration     │      │  Functional      │
│  Specialist   │      │  Test Specialist │      │  Test Specialist │
│               │      │                  │      │                  │
│ Model: same   │      │  Model: same     │      │  Model: same     │
│ Specialized   │      │  Specialized     │      │  Specialized     │
│ System Prompt │      │  System Prompt   │      │  System Prompt   │
└───────┬───────┘      └────────┬─────────┘      └────────┬─────────┘
        │                       │                         │
        │                       │                         │
        └───────────────────────┴─────────────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  AGGREGATED RESULTS   │
                    │  Back to Main Agent   │
                    └───────────────────────┘
```

---

## 🔄 Middleware Fallback Flow (Deep Dive)

### **Step 1: Model Creation & Middleware Setup**

```
┌─────────────────────────────────────────────────────────────────┐
│  PRIMARY_MODEL = "openai:gpt-4o-mini"                           │
│  FALLBACK_MODELS = ["openai:gpt-WRONG-1", "openai:gpt-WRONG-2"]│
│                                                                  │
│  middleware = ModelFallbackMiddleware(*FALLBACK_MODELS)         │
│  ↓                                                               │
│  Middleware wraps the model call                                │
└─────────────────────────────────────────────────────────────────┘
```

### **Step 2: Request Execution with Middleware Interception**

```
USER REQUEST
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LangGraph Agent Runtime                       │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  1. before_agent hook (if any)                             │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│                              ▼                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  2. before_model hook (SummarizationMiddleware, etc.)     │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│                              ▼                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  3. wrap_model_call (ModelFallbackMiddleware)             │ │
│  │                                                            │ │
│  │     ┌──────────────────────────────────────────────────┐  │ │
│  │     │  Try: PRIMARY_MODEL                              │  │ │
│  │     │    ↓                                             │  │ │
│  │     │  POST https://api.openai.com/v1/chat/...        │  │ │
│  │     │    model: "gpt-4o-mini"                          │  │ │
│  │     │    ↓                                             │  │ │
│  │     │  Response: HTTP 200 OK ✅                        │  │ │
│  │     │    ↓                                             │  │ │
│  │     │  Return Success → Use Primary Model              │  │ │
│  │     │                                                   │  │ │
│  │     │  (Fallbacks NEVER TRIED!)                        │  │ │
│  │     └──────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│                              ▼                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  4. Model processes request and generates response        │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│                              ▼                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  5. after_model hook (validation, guardrails)             │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│                              ▼                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  6. Tool execution (if model calls tools)                 │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│                              ▼                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  7. after_agent hook (cleanup, logging)                   │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                               ▼
                         FINAL RESPONSE
```

---

## 🚨 What Happens When Primary Model FAILS

### **Scenario: Primary Model is WRONG**

```
PRIMARY_MODEL = "openai:gpt-4o-mini-WRONG-MODEL"  ❌
FALLBACK_MODELS = ["openai:gpt-4o-mini", "openai:gpt-3.5-turbo"]  ✅
```

### **Execution Flow:**

```
┌─────────────────────────────────────────────────────────────────┐
│  wrap_model_call (ModelFallbackMiddleware)                      │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ TRY #1: PRIMARY_MODEL                                      │ │
│  │   ↓                                                        │ │
│  │ POST https://api.openai.com/v1/chat/completions           │ │
│  │   model: "gpt-4o-mini-WRONG-MODEL"                        │ │
│  │   ↓                                                        │ │
│  │ Response: HTTP 404 Not Found ❌                            │ │
│  │   Error: "Model does not exist"                           │ │
│  │   ↓                                                        │ │
│  │ Middleware catches exception!                             │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                 │                                │
│                                 ▼                                │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ TRY #2: FALLBACK_MODELS[0]                                │ │
│  │   ↓                                                        │ │
│  │ POST https://api.openai.com/v1/chat/completions           │ │
│  │   model: "gpt-4o-mini"                                    │ │
│  │   ↓                                                        │ │
│  │ Response: HTTP 200 OK ✅                                   │ │
│  │   Success! Use this model                                 │ │
│  │   ↓                                                        │ │
│  │ Return Success → Continue with Fallback Model             │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘

RESULT: System continues working seamlessly! 🎉
```

---

## 🔧 Internal Components Breakdown

### **1. LangGraph State Management**

```python
class DeepAgentState(TypedDict):
    messages: list[BaseMessage]  # Conversation history
    files: dict                   # File system access
    todos: list[dict]             # Planning/task tracking
    # ... other state
```

### **2. Built-in Tools**

```
┌──────────────────────────────────────────────┐
│  write_todos     │ Create task plans         │
│  update_todos    │ Update task status        │
│  task()          │ Delegate to sub-agents    │
│  plan            │ Strategic planning        │
│  write_file      │ File system write         │
│  read_file       │ File system read          │
│  list_directory  │ File system list          │
└──────────────────────────────────────────────┘
```

### **3. Middleware Stack (Execution Order)**

```
Request
  │
  ▼
┌─────────────────────────────────────────┐
│ 1. SummarizationMiddleware              │
│    - Condenses long conversations       │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ 2. ModelFallbackMiddleware              │
│    - Handles model failures             │
│    - Tries fallback models              │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ 3. PlanningMiddleware (built-in)        │
│    - Manages planning tool              │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ 4. FilesystemMiddleware (built-in)      │
│    - Manages file operations            │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ 5. SubagentMiddleware (built-in)        │
│    - Manages task() tool                │
│    - Handles sub-agent delegation       │
└───────────────┬─────────────────────────┘
                │
                ▼
            ACTUAL MODEL CALL
```

---

## 🎯 task() Tool - Sub-Agent Delegation

### **How Main Agent Delegates to Sub-Agents**

```
Main Agent Tool Call:
┌──────────────────────────────────────────────────────────────┐
│ task(                                                         │
│   description="Generate E2E test scenarios...",              │
│   subagent_type="e2e_test_specialist"                       │
│ )                                                            │
└──────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────┐
│  SubagentMiddleware intercepts                                │
│    1. Finds sub-agent config by name                         │
│    2. Creates isolated context                               │
│    3. Invokes sub-agent with task description                │
│    4. Returns sub-agent response                             │
└──────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────┐
│  E2E Test Specialist Sub-Agent                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ Model: gpt-4o-mini                                     │  │
│  │ System Prompt: E2E_SYSTEM_PROMPT                       │  │
│  │ Context: Isolated from main agent                      │  │
│  │ Task: "Generate E2E test scenarios..."                │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  Generates: Detailed E2E test scenarios                      │
└──────────────────────────────────────────────────────────────┘
                        │
                        ▼
            Returns to Main Agent as ToolMessage
```

---

## 🔄 Complete Request-Response Cycle

```
┌────────────────────────────────────────────────────────────────┐
│                    USER SUBMITS REQUEST                         │
└──────────────────────────┬─────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────────┐
│  agent.invoke({"messages": [...]})                             │
└──────────────────────────┬─────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────────┐
│  LangGraph Runtime Starts                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ State Initialization                                     │  │
│  │   messages: [HumanMessage(...)]                          │  │
│  │   files: {}                                              │  │
│  │   todos: []                                              │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────────────────┬─────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────────┐
│  LOOP: Agent Execution Cycle                                   │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ STEP 1: Main Agent thinks                                │ │
│  │   → Middleware: SummarizationMiddleware                  │ │
│  │   → Middleware: ModelFallbackMiddleware (wrap_model_call)│ │
│  │     ├─ Try PRIMARY_MODEL                                 │ │
│  │     │   └─ Success? Continue                             │ │
│  │     │   └─ Fail? Try FALLBACK_MODELS[0]                  │ │
│  │   → Model generates response with tool calls             │ │
│  │   → State updated with AIMessage                         │ │
│  └───────────────────────────────────────────────────────────┘ │
│                           │                                     │
│                           ▼                                     │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ STEP 2: Tool Execution                                    │ │
│  │   Tool: write_todos                                       │ │
│  │     → Creates task breakdown                             │ │
│  │   State updated with ToolMessage                          │ │
│  └───────────────────────────────────────────────────────────┘ │
│                           │                                     │
│                           ▼                                     │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ STEP 3: Main Agent thinks again                           │ │
│  │   → Reviews todo list                                     │ │
│  │   → Decides to delegate                                   │ │
│  │   → Generates tool calls for task()                       │ │
│  └───────────────────────────────────────────────────────────┘ │
│                           │                                     │
│                           ▼                                     │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ STEP 4: Sub-Agent Delegation (Parallel)                   │ │
│  │                                                            │ │
│  │   Tool: task(subagent_type="e2e_test_specialist")        │ │
│  │     ↓                                                      │ │
│  │   SubagentMiddleware creates E2E sub-agent               │ │
│  │     → Isolated context                                    │ │
│  │     → E2E_SYSTEM_PROMPT                                   │ │
│  │     → Generates E2E scenarios                             │ │
│  │     → Returns ToolMessage                                 │ │
│  │                                                            │ │
│  │   Tool: task(subagent_type="integration_test_specialist") │ │
│  │     ↓                                                      │ │
│  │   SubagentMiddleware creates Integration sub-agent        │ │
│  │     → Generates Integration scenarios                     │ │
│  │     → Returns ToolMessage                                 │ │
│  │                                                            │ │
│  │   Tool: task(subagent_type="functional_test_specialist")  │ │
│  │     ↓                                                      │ │
│  │   SubagentMiddleware creates Functional sub-agent         │ │
│  │     → Generates Functional scenarios                      │ │
│  │     → Returns ToolMessage                                 │ │
│  └───────────────────────────────────────────────────────────┘ │
│                           │                                     │
│                           ▼                                     │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ STEP 5: Main Agent aggregates results                     │ │
│  │   → Reviews all 3 sub-agent responses                     │ │
│  │   → Synthesizes comprehensive test strategy               │ │
│  │   → Generates final response (no tool calls)              │ │
│  │   → STOP condition met                                    │ │
│  └───────────────────────────────────────────────────────────┘ │
└──────────────────────────┬─────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────────┐
│  FINAL STATE                                                    │
│  {                                                              │
│    messages: [                                                  │
│      HumanMessage(...),                                         │
│      AIMessage(tool_calls=[write_todos]),                       │
│      ToolMessage(write_todos result),                           │
│      AIMessage(tool_calls=[task(), task(), task()]),            │
│      ToolMessage(E2E results),                                  │
│      ToolMessage(Integration results),                          │
│      ToolMessage(Functional results),                           │
│      AIMessage(final_comprehensive_strategy)  ← FINAL          │
│    ],                                                           │
│    todos: [...],                                                │
│    files: {}                                                    │
│  }                                                              │
└────────────────────────────────────────────────────────────────┘
```

---

## 📊 Dynamic Fallback in Fallback Function

### **When DeepAgents Fails Completely**

If the deepagents system encounters an error (e.g., LangGraph issues), we have a fallback that also uses dynamic model selection:

```python
def get_working_model(temperature=0.7):
    """
    Dynamically find and return a working model.
    Tries: [PRIMARY_MODEL] + FALLBACK_MODELS
    """
    all_models = [PRIMARY_MODEL] + FALLBACK_MODELS
    
    for model_name in all_models:
        try:
            model = init_chat_model(model_name, temperature=temperature)
            return model  # ✅ Success!
        except:
            continue  # ❌ Failed, try next
    
    raise RuntimeError("All models failed!")
```

### **Flow:**

```
DeepAgents Error
      │
      ▼
┌─────────────────────────────────────────────┐
│  run_fallback_multi_agent_system()          │
│                                              │
│  For each sub-agent:                         │
│    1. Call get_working_model()               │
│       ├─ Try: PRIMARY_MODEL                  │
│       │   └─ Success? Return it ✅           │
│       │   └─ Fail? Try next                  │
│       ├─ Try: FALLBACK_MODELS[0]             │
│       │   └─ Success? Return it ✅           │
│       │   └─ Fail? Try next                  │
│       └─ Try: FALLBACK_MODELS[1]             │
│           └─ Success? Return it ✅           │
│           └─ Fail? Raise error               │
│                                              │
│    2. Use returned model to generate results │
│    3. Collect all results                    │
└─────────────────────────────────────────────┘
```

---

## 🎓 Key Takeaways

### **1. Middleware is Transparent**
- Models don't know they're wrapped
- Fallback happens automatically
- No code changes needed when adding/removing models

### **2. Context Isolation**
- Sub-agents have separate contexts
- Main agent's context stays clean
- Each specialist focuses on its domain

### **3. Resilience Through Layering**
- Layer 1: ModelFallbackMiddleware in deepagents
- Layer 2: Dynamic model selection in fallback function
- Layer 3: Error handling and user-friendly messages

### **4. Dynamic Adaptation**
```python
# ✅ PRIMARY is correct, FALLBACKS are wrong
PRIMARY = "openai:gpt-4o-mini"           # Used, fallbacks never tried
FALLBACKS = ["openai:wrong1", "wrong2"]  # Ignored

# ✅ PRIMARY is wrong, FALLBACKS are correct
PRIMARY = "openai:gpt-WRONG"             # Fails, tries fallbacks
FALLBACKS = ["openai:gpt-4o-mini"]       # Used automatically

# ✅ ALL are wrong except last
PRIMARY = "openai:wrong"                 # Fails
FALLBACKS = ["openai:wrong2", "gpt-4o"]  # Tries all, uses last one
```

---

## 🚀 Summary

**DeepAgents Workflow:**
1. User sends request
2. Main agent analyzes and creates plan
3. Main agent delegates to sub-agents using `task()` tool
4. SubagentMiddleware manages delegation
5. Each sub-agent processes in isolation
6. Main agent aggregates all responses
7. Returns comprehensive result

**Middleware Fallback:**
- Wraps every model call
- Catches failures automatically
- Tries fallback models in order
- Transparent to the rest of the system
- Works at **runtime** - no code changes needed!

---

**Status**: ✅ Fully Dynamic, Self-Healing, Production-Ready System!

