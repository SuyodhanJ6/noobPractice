"""
AI Chatbot using LangChain create_agent
A comprehensive chatbot that can answer user questions using various tools.
"""

import os
from dataclasses import dataclass
from typing import Optional
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.tools import tool, ToolRuntime
from langgraph.checkpoint.memory import InMemorySaver
from dotenv import load_dotenv
load_dotenv()

# Define context schema for user information
@dataclass
class Context:
    """Custom runtime context schema."""
    user_id: str
    user_name: Optional[str] = None


# Define system prompt for the chatbot
SYSTEM_PROMPT = """You are a helpful AI assistant chatbot that can answer user questions and help with various tasks.

You have access to several tools:

- search_web: Use this to search for current information on the web
- calculate: Use this to perform mathematical calculations
- get_time: Use this to get the current time
- get_user_info: Use this to get information about the current user
- explain_concept: Use this to explain technical concepts in simple terms

Always be helpful, friendly, and provide accurate information. If you're not sure about something, say so rather than guessing.
When using tools, explain what you're doing to the user."""


# Define tools for the chatbot
@tool
def search_web(query: str) -> str:
    """Search the web for current information on a given topic."""
    # In a real implementation, you would integrate with a search API
    # For now, we'll simulate a search result
    return f"Search results for '{query}': This is a simulated search result. In a real implementation, this would connect to a search API like Google Search or Bing."


@tool
def calculate(expression: str) -> str:
    """Perform mathematical calculations safely."""
    try:
        # Simple evaluation for basic math operations
        # In production, use a proper math parser for security
        allowed_chars = set('0123456789+-*/.() ')
        if all(c in allowed_chars for c in expression):
            result = eval(expression)
            return f"Result: {result}"
        else:
            return "Error: Invalid characters in expression. Only numbers and basic operators (+, -, *, /, parentheses) are allowed."
    except Exception as e:
        return f"Error calculating '{expression}': {str(e)}"


@tool
def get_time() -> str:
    """Get the current time."""
    from datetime import datetime
    now = datetime.now()
    return f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}"


@tool
def get_user_info(runtime: ToolRuntime) -> str:
    """Get information about the current user."""
    user_id = runtime.context.user_id
    user_name = runtime.context.user_name or "Unknown"
    return f"User ID: {user_id}, Name: {user_name}"


@tool
def explain_concept(concept: str) -> str:
    """Explain a technical concept in simple terms."""
    explanations = {
        "ai": "Artificial Intelligence (AI) is technology that enables machines to perform tasks that typically require human intelligence, like learning, reasoning, and problem-solving.",
        "machine learning": "Machine Learning is a subset of AI where computers learn patterns from data without being explicitly programmed for each task.",
        "neural network": "A Neural Network is a computing system inspired by the human brain, consisting of interconnected nodes (neurons) that process information.",
        "python": "Python is a popular programming language known for its simplicity and readability, widely used in data science, web development, and AI.",
        "langchain": "LangChain is a framework for building applications with Large Language Models (LLMs), providing tools to create AI agents and chatbots."
    }
    
    concept_lower = concept.lower()
    if concept_lower in explanations:
        return explanations[concept_lower]
    else:
        return f"I can explain '{concept}' in simple terms: This is a general explanation. For specific technical concepts, I'd need more context about what aspect you'd like me to focus on."


# Define response format
@dataclass
class ResponseFormat:
    """Response schema for the agent."""
    response: str
    confidence: str = "high"  # high, medium, low
    tools_used: Optional[str] = None


def create_chatbot():
    """Create and return a configured chatbot agent."""
    
    # Configure the model
    model = init_chat_model(
        "openai:gpt-4o-mini",  # Using OpenAI GPT-4o mini model
        temperature=0.7
    )
    
    # Set up memory for conversation history
    checkpointer = InMemorySaver()
    
    # Create the agent
    agent = create_agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[search_web, calculate, get_time, get_user_info, explain_concept],
        context_schema=Context,
        response_format=ResponseFormat,
        checkpointer=checkpointer
    )
    
    return agent


def run_chatbot():
    """Run the chatbot in an interactive loop."""
    print("🤖 AI Chatbot Started!")
    print("Type 'quit' or 'exit' to stop the chatbot.")
    print("=" * 50)
    
    # Create the chatbot
    agent = create_chatbot()
    
    # Configuration for the conversation
    config = {"configurable": {"thread_id": "main_conversation"}}
    context = Context(user_id="user_001", user_name="User")
    
    while True:
        try:
            # Get user input
            user_input = input("\n👤 You: ").strip()
            
            # Check for exit commands
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("🤖 Chatbot: Goodbye! Have a great day!")
                break
            
            if not user_input:
                continue
            
            # Get response from the agent
            response = agent.invoke(
                {"messages": [{"role": "user", "content": user_input}]},
                config=config,
                context=context
            )
            
            # Display the response
            if 'structured_response' in response:
                structured_resp = response['structured_response']
                print(f"\n🤖 Chatbot: {structured_resp.response}")
                if structured_resp.tools_used:
                    print(f"🔧 Tools used: {structured_resp.tools_used}")
            else:
                print(f"\n🤖 Chatbot: {response}")
                
        except KeyboardInterrupt:
            print("\n\n🤖 Chatbot: Goodbye! Have a great day!")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            print("Please try again or type 'quit' to exit.")


if __name__ == "__main__":
    # Set up environment variables if needed
    # You can set your API keys here or in a .env file
    # os.environ["OPENAI_API_KEY"] = "your-api-key-here"
    
    run_chatbot()
