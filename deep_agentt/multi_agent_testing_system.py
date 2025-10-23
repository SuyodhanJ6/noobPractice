"""
Multi-Agent Testing System using deepagents
==========================================

Architecture:
- Main Agent: Orchestrator (keeps track of complexity, delegates to sub-agents)
- Sub-Agent 1: E2E Test Scenario Generator
- Sub-Agent 2: Integration Test Generator
- Sub-Agent 3: Functional Test Generator

Usage:
    python multi_agent_testing_system.py

Documentation:
    - init_chat_model: Universal LLM provider interface
    - Format: "provider:model_name" (e.g., "openai:gpt-4o-mini", "anthropic:claude-3-5-haiku-latest")
    - Automatically handles authentication via environment variables
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv
import os
import json
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# ============================================================================
# MODEL CONFIGURATION WITH FALLBACK
# ============================================================================

# Model configuration with fallback chain
# TEST CASE: Primary is CORRECT, fallbacks are WRONG
# Expected: System uses primary, never tries fallbacks!
PRIMARY_MODEL = "openai:gpt-4o-mini"  # ✅ Valid model (should work!)
FALLBACK_MODELS = [
    "openai:gpt-WRONG-1",    # ❌ Fallback 1: Wrong (won't be tried!)
    "openai:gpt-WRONG-2",    # ❌ Fallback 2: Wrong (won't be tried!)
]
DEFAULT_TEMPERATURE = 0.7


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class UserStory:
    """User story with complexity assessment"""
    story: str
    project_context: str
    complexity: str = "medium"  # low, medium, high, critical


# ============================================================================
# MODEL FACTORY
# ============================================================================

def create_model(temperature: float = DEFAULT_TEMPERATURE):
    """Create a model (primary model for agents)"""
    logger.info(f"🤖 Creating model: {PRIMARY_MODEL}")
    model = init_chat_model(PRIMARY_MODEL, temperature=temperature)
    logger.info(f"✅ Model created successfully")
    return model




# ============================================================================
# MULTI-AGENT SYSTEM USING deepagents
# ============================================================================

# Define sub-agent system prompts

E2E_SYSTEM_PROMPT = """You are an Expert End-to-End (E2E) Test Specialist.

EXPERTISE:
- Design complete user journey test scenarios
- Map critical user paths through the application
- Define flow diagrams for test execution
- Identify edge cases in user workflows
- Ensure comprehensive coverage of user interactions

RESPONSE FORMAT:
Provide test scenarios organized as:
1. End-to-End Scenarios (numbered list of complete workflows)
2. User Journey Flows (step-by-step sequences)
3. Critical Paths (most important paths that must work)
4. Success Criteria (how to verify each scenario passes)
"""

INTEGRATION_SYSTEM_PROMPT = """You are an Expert Integration Test Specialist.

EXPERTISE:
- Design API integration tests
- Test database interactions and consistency
- Verify service-to-service communications
- Validate data flows between systems
- Test third-party integrations
- Ensure data consistency across services

RESPONSE FORMAT:
Provide test scenarios organized as:
1. API Integration Tests (numbered list of API test cases)
2. Database Tests (data persistence and retrieval tests)
3. Service Interactions (cross-service communication tests)
4. Data Consistency Checks (data integrity validation)
"""

FUNCTIONAL_SYSTEM_PROMPT = """You are an Expert Functional Test Specialist.

EXPERTISE:
- Design functional feature tests
- Identify edge cases and boundary conditions
- Define input validation rules
- Plan error handling scenarios
- Ensure all feature requirements are testable
- Verify business logic correctness

RESPONSE FORMAT:
Provide test scenarios organized as:
1. Feature Tests (core feature functionality tests)
2. Edge Cases (boundary and edge case tests)
3. Input Validation Tests (validation rule tests)
4. Error Handling Tests (exception and error scenarios)
"""

MAIN_AGENT_SYSTEM_PROMPT = """You are a Test Strategy Orchestrator coordinating a team of specialist agents.

YOUR ROLE:
- Receive user stories and project context
- Assess complexity level
- Delegate testing responsibilities to specialist sub-agents using the task() tool
- Coordinate responses from all specialists
- Ensure comprehensive test coverage

AVAILABLE SUB-AGENTS:
- e2e_test_specialist: Generates end-to-end test scenarios based on user journeys and critical paths
- integration_test_specialist: Generates integration test scenarios for APIs, databases, and service interactions  
- functional_test_specialist: Generates functional test scenarios for features, edge cases, and error handling

IMPORTANT: For complex tasks, delegate to your subagents using the task() tool.
This keeps your context clean and improves results.

COMPLEXITY ASSESSMENT:
- Low: Simple features, basic happy path testing
- Medium: Standard features, multiple paths, some edge cases
- High: Complex features, many interactions, critical paths
- Critical: Business-critical, security-sensitive, performance-critical

DELEGATION STRATEGY:
1. Use task(name="e2e_test_specialist", task="Generate end-to-end test scenarios for [specific requirements]")
2. Use task(name="integration_test_specialist", task="Generate integration test scenarios for [specific requirements]")
3. Use task(name="functional_test_specialist", task="Generate functional test scenarios for [specific requirements]")
4. Aggregate and synthesize all responses into a comprehensive test strategy

When complexity is HIGH or CRITICAL:
- Request more comprehensive scenarios from each sub-agent
- Ensure edge cases are thoroughly covered
- Validate integration points are well-tested
"""


def create_multi_agent_system():
    """
    Create the complete multi-agent system using deepagents with ModelFallbackMiddleware.
    
    Uses ModelFallbackMiddleware for automatic failover:
    - Primary: gpt-4o-mini (fast and cost-effective)
    - Fallback 1: gpt-3.5-turbo (cheaper backup)
    - Fallback 2: gpt-4o (more capable if cheaper models fail)
    """
    from deepagents import create_deep_agent
    from langchain.agents.middleware import ModelFallbackMiddleware
    
    # Create models
    print("\n🤖 Creating models with fallback middleware...")
    print(f"   Primary: {PRIMARY_MODEL}")
    print(f"   Fallbacks: {FALLBACK_MODELS}")
    
    main_model = create_model(temperature=0.7)
    e2e_model = create_model(temperature=0.7)
    integration_model = create_model(temperature=0.7)
    functional_model = create_model(temperature=0.7)
    
    # Create fallback middleware (as per LangChain docs)
    # Accepts variable number of fallback model strings
    fallback_middleware = ModelFallbackMiddleware(*FALLBACK_MODELS)
    logger.info("✅ ModelFallbackMiddleware created with fallback chain")
    
    # Create sub-agent configurations with detailed descriptions
    # NOTE: Descriptions are static but main agent extracts specifics from user story dynamically
    subagents = [
        {
            "name": "e2e_test_specialist",
            "description": """Generates end-to-end test scenarios based on complete user journeys and critical paths.
            Focuses on: Full user workflows, UI interactions, multi-step processes, cross-page navigation.
            Use when: User story involves user-facing features, complete workflows, or critical user paths.
            Will adapt to: Specific features, pages, and user flows mentioned in the story.""",
            "system_prompt": E2E_SYSTEM_PROMPT,
            "tools": [],
            "model": e2e_model,
        },
        {
            "name": "integration_test_specialist",
            "description": """Generates integration test scenarios for APIs, databases, microservices, and external service interactions.
            Focuses on: API contracts, database transactions, service-to-service communication, third-party integrations.
            Use when: User story involves backend APIs, database operations, external services, or data flow between components.
            Will adapt to: Specific APIs, databases, and services mentioned in the project context.""",
            "system_prompt": INTEGRATION_SYSTEM_PROMPT,
            "tools": [],
            "model": integration_model,
        },
        {
            "name": "functional_test_specialist",
            "description": """Generates functional test scenarios for business logic, feature behavior, edge cases, and error handling.
            Focuses on: Input validation, business rules, error conditions, boundary cases, security checks.
            Use when: User story involves business logic, data validation, error scenarios, or specific feature requirements.
            Will adapt to: Specific business rules, validation requirements, and edge cases from the story.""",
            "system_prompt": FUNCTIONAL_SYSTEM_PROMPT,
            "tools": [],
            "model": functional_model,
        }
    ]
    
    # Create deep agent with middleware (as per LangChain docs)
    agent = create_deep_agent(
        model=main_model,
        system_prompt=MAIN_AGENT_SYSTEM_PROMPT,
        tools=[],
        subagents=subagents,
        middleware=[fallback_middleware],  # Add fallback middleware here
    )
    
    print("✅ Multi-agent system created with ModelFallbackMiddleware")
    return agent


def run_multi_agent_system(user_story: str, project_context: str, complexity: str = "medium"):
    """
    Run the complete multi-agent system.
    
    Process:
    1. Main agent receives user story and context
    2. Main agent assesses complexity
    3. Main agent orchestrates 3 sub-agents
    4. Each sub-agent generates specialized test scenarios
    5. Results are aggregated and returned
    """
    
    print("\n" + "="*80)
    print("PART 2: MULTI-AGENT SYSTEM (Using deepagents)")
    print("="*80)
    
    try:
        print("\n[ORCHESTRATION] Creating multi-agent system...")
        agent = create_multi_agent_system()
        print("✅ Multi-agent system created")
        
        # Create the user request for the main agent
        user_request = f"""
Generate comprehensive test scenarios for the following:

USER STORY:
{user_story}

PROJECT CONTEXT:
{project_context}

COMPLEXITY LEVEL: {complexity.upper()}

INSTRUCTIONS:
1. Assess the complexity and requirements
2. Use the task() tool to delegate to each sub-agent:
   - task(name="e2e_test_specialist", task="Generate end-to-end test scenarios for this user story")
   - task(name="integration_test_specialist", task="Generate integration test scenarios for this user story")  
   - task(name="functional_test_specialist", task="Generate functional test scenarios for this user story")
3. Aggregate and synthesize all responses into a comprehensive test strategy
4. Ensure complete test coverage based on the complexity level

Coordinate your responses to ensure comprehensive test coverage.
"""
        
        print("\n[MAIN AGENT] Processing request and orchestrating sub-agents...")
        print(f"Complexity Level: {complexity.upper()}")
        
        # Invoke the agent
        response = agent.invoke({
            "messages": [{"role": "user", "content": user_request}]
        })
        
        print("\n✅ Multi-agent orchestration complete")
        
        return response
        
    except Exception as e:
        print(f"\n❌ Error in multi-agent system: {str(e)}")
        print("Note: deepagents requires proper LangGraph setup")
        print("Falling back to direct sub-agent calls...")
        
        # Fallback: Call sub-agents directly
        return run_fallback_multi_agent_system(user_story, project_context, complexity)


def get_working_model(temperature: float = DEFAULT_TEMPERATURE):
    """
    Dynamically find and return a working model.
    Tries primary first, then fallbacks automatically - NO code changes needed!
    """
    all_models = [PRIMARY_MODEL] + FALLBACK_MODELS
    
    for model_name in all_models:
        try:
            logger.info(f"🔄 Trying model: {model_name}")
            model = init_chat_model(model_name, temperature=temperature)
            logger.info(f"✅ Model {model_name} is working!")
            return model
        except Exception as e:
            logger.warning(f"⚠️  Model {model_name} failed: {str(e)}")
            continue
    
    raise RuntimeError("❌ All models failed! No working model available.")


def run_fallback_multi_agent_system(user_story: str, project_context: str, complexity: str):
    """
    Fallback implementation that calls sub-agents directly.
    Dynamically selects working models - adapts automatically!
    """
    from langchain_core.messages import SystemMessage, HumanMessage
    
    print("\n[FALLBACK] Using direct sub-agent calls with dynamic model selection...")
    
    context = f"""
USER STORY:
{user_story}

PROJECT CONTEXT:
{project_context}

COMPLEXITY LEVEL: {complexity.upper()}
"""
    
    results = {}
    
    # Sub-Agent 1: E2E Testing
    print("\n[SUB-AGENT 1] E2E Test Specialist - Generating scenarios...")
    e2e_model = get_working_model(temperature=0.7)
    e2e_messages = [
        SystemMessage(content=E2E_SYSTEM_PROMPT),
        HumanMessage(content=context)
    ]
    e2e_response = e2e_model.invoke(e2e_messages)
    results["e2e_tests"] = e2e_response.content
    print("✅ E2E scenarios generated")
    
    # Sub-Agent 2: Integration Testing
    print("[SUB-AGENT 2] Integration Test Specialist - Generating scenarios...")
    integration_model = get_working_model(temperature=0.7)
    integration_messages = [
        SystemMessage(content=INTEGRATION_SYSTEM_PROMPT),
        HumanMessage(content=context)
    ]
    integration_response = integration_model.invoke(integration_messages)
    results["integration_tests"] = integration_response.content
    print("✅ Integration scenarios generated")
    
    # Sub-Agent 3: Functional Testing
    print("[SUB-AGENT 3] Functional Test Specialist - Generating scenarios...")
    functional_model = get_working_model(temperature=0.7)
    functional_messages = [
        SystemMessage(content=FUNCTIONAL_SYSTEM_PROMPT),
        HumanMessage(content=context)
    ]
    functional_response = functional_model.invoke(functional_messages)
    results["functional_tests"] = functional_response.content
    print("✅ Functional scenarios generated")
    
    return results


def display_results(results):
    """Display all test scenarios in a clean, readable format"""
    print("\n" + "="*80)
    print("🎯 FINAL TEST SCENARIOS - AGGREGATED FROM ALL SUB-AGENTS")
    print("="*80)
    
    # Extract content from deepagents response structure
    if isinstance(results, dict) and "messages" in results:
        # This is a deepagents response - extract the final AI message content
        messages = results.get("messages", [])
        final_message = None
        
        # Find the last AIMessage in the conversation
        for msg in reversed(messages):
            if hasattr(msg, 'content') and msg.content and not hasattr(msg, 'tool_calls'):
                final_message = msg.content
                break
        
        if final_message:
            print("\n" + "─"*80)
            print("📋 COMPREHENSIVE TEST SCENARIOS SUMMARY")
            print("─"*80)
            print(final_message)
        else:
            print("No test scenarios found in response")
            
        # Also show individual sub-agent responses if available
        tool_messages = [msg for msg in messages if hasattr(msg, 'name') and msg.name == 'task']
        if tool_messages:
            print("\n" + "─"*80)
            print("📌 DETAILED SUB-AGENT RESPONSES")
            print("─"*80)
            
            for i, tool_msg in enumerate(tool_messages, 1):
                print(f"\n[SUB-AGENT {i}] {tool_msg.name.upper()}")
                print("-" * 40)
                print(tool_msg.content)
    
    elif isinstance(results, dict) and "e2e_tests" in results:
        # This is a fallback response
        print("\n" + "─"*80)
        print("📌 E2E TEST SCENARIOS")
        print("─"*80)
        print(results.get("e2e_tests", "No E2E scenarios generated"))
        
        print("\n" + "─"*80)
        print("🔗 INTEGRATION TEST SCENARIOS")
        print("─"*80)
        print(results.get("integration_tests", "No integration scenarios generated"))
        
        print("\n" + "─"*80)
        print("⚙️  FUNCTIONAL TEST SCENARIOS")
        print("─"*80)
        print(results.get("functional_tests", "No functional scenarios generated"))
    
    else:
        print("Unexpected response format - displaying raw results:")
        print(results)


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    # Sample data
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
    
    # ========================================================================
    # EXECUTION FLOW
    # ========================================================================
    
    # Run Multi-Agent System
    results = run_multi_agent_system(USER_STORY, PROJECT_CONTEXT, complexity="high")
    
    # Display Results
    display_results(results)
    
    # Summary
    print("\n" + "="*80)
    print("✅ MULTI-AGENT TESTING SYSTEM EXECUTION FINISHED")
    print("="*80)
    print("\nSYSTEM COMPONENTS:")
    print("  ✓ Multi-Agent System with 3 Specialists:")
    print("    - E2E Test Scenario Specialist")
    print("    - Integration Test Specialist")
    print("    - Functional Test Specialist")
    print("\nMain Agent responsibilities:")
    print("  ✓ Receives user story and project context")
    print("  ✓ Assesses complexity level")
    print("  ✓ Orchestrates all sub-agents")
    print("  ✓ Aggregates test scenarios")
    print("="*80)
