"""
FastAPI Chatbot using LangChain create_agent
A REST API endpoint for the AI chatbot.
"""

import os
from dataclasses import dataclass
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.tools import tool, ToolRuntime
from langgraph.checkpoint.memory import InMemorySaver
from dotenv import load_dotenv
from feedback_system import FeedbackManager, FeedbackData, create_feedback_id
from logging_config import log_api_request, log_api_response, log_error, log_chat_interaction, log_feedback, log_recursion_limit
from chat_storage import chat_storage
from error_handling_middleware import create_error_handling_middleware, create_simple_error_handler
from langchain.agents.middleware import ModelCallLimitMiddleware
from playbook_manager import playbook_manager
from ace_pipeline import ace_pipeline
import time
import traceback

load_dotenv()


def _get_fallback_response(message: str) -> str:
    """Generate appropriate fallback response based on question type."""
    message_lower = message.lower()
    
    if any(word in message_lower for word in ["calculate", "math", "add", "subtract", "multiply", "divide"]):
        return "I'm having trouble with calculations right now. Please try a simpler math problem or use a calculator."
    
    elif any(word in message_lower for word in ["time", "date", "clock"]):
        return "I can't get the current time right now. Please check your device's clock."
    
    elif any(word in message_lower for word in ["search", "find", "look up"]):
        return "I'm unable to search the web at the moment. Please try asking a general knowledge question instead."
    
    elif any(word in message_lower for word in ["explain", "what is", "define", "meaning"]):
        return "I'm having trouble explaining concepts right now. You might want to search online for more information."
    
    else:
        return "I apologize, but I'm having trouble processing your request right now. Please try rephrasing your question or ask something simpler."


# Define context schema for user information
@dataclass
class Context:
    """Custom runtime context schema."""
    user_id: str
    user_name: Optional[str] = None


# Define base system prompt for the chatbot
BASE_SYSTEM_PROMPT = """You are a helpful AI assistant chatbot with access to a curated playbook of strategies.

Available tools:
- search_web: Search for current information on the web
- calculate: Perform mathematical calculations  
- get_time: Get the current time
- get_user_info: Get information about the current user
- explain_concept: Explain technical concepts in simple terms

IMPORTANT RULES:
1. Read the playbook bullets carefully and apply relevant strategies
2. Use bullet points in explanations when helpful
3. Answer questions directly without unnecessary tool calls
4. Use tools only when specifically needed
5. After getting tool results, provide a final answer and STOP
6. Do not call the same tool multiple times
7. Be concise and helpful

If you can answer a question directly, do so without using tools."""


def get_enhanced_system_prompt(user_question: str) -> str:
    """Get system prompt enhanced with relevant playbook bullets"""
    
    # Retrieve relevant bullets from playbook
    relevant_bullets = playbook_manager.retrieve_relevant(user_question, top_k=10)
    
    if not relevant_bullets:
        return BASE_SYSTEM_PROMPT
    
    # Build playbook section
    playbook_section = "\n\nPLAYBOOK (Relevant Strategies):\n"
    for bullet in relevant_bullets:
        playbook_section += f"- {bullet.content}\n"
    
    # Combine base prompt with playbook
    enhanced_prompt = BASE_SYSTEM_PROMPT + playbook_section
    
    return enhanced_prompt


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


# Pydantic models for FastAPI
class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = "default_user"
    user_name: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    confidence: str
    tools_used: Optional[str] = None
    success: bool = True
    feedback_id: Optional[str] = None  # For feedback tracking


class FeedbackRequest(BaseModel):
    feedback_id: str
    user_feedback: str
    feedback_type: str  # "correct", "incorrect", "partially_correct", "improvement_suggestion"
    rating: Optional[int] = None  # 1-5 scale
    additional_notes: Optional[str] = None


class FeedbackResponse(BaseModel):
    success: bool
    message: str
    feedback_id: Optional[str] = None


# Global chatbot instance
chatbot_agent = None
checkpointer = InMemorySaver()
feedback_manager = FeedbackManager()


def create_chatbot(user_question: str = ""):
    """Create and return a configured chatbot agent with playbook-enhanced system prompt."""
    global chatbot_agent
    
    # Configure the model
    model = init_chat_model(
        "openai:gpt-4o-mini",  # Using OpenAI GPT-4o mini model
        temperature=0.7
    )
    
    # Get enhanced system prompt with relevant playbook bullets
    enhanced_prompt = get_enhanced_system_prompt(user_question)
    
    # Create the agent with error handling and model call limit middleware
    chatbot_agent = create_agent(
        model=model,
        debug=True,
        system_prompt=enhanced_prompt,
        tools=[search_web, calculate, get_time, get_user_info, explain_concept],
        context_schema=Context,
        response_format=ResponseFormat,
        checkpointer=checkpointer,
        middleware=[
            # Prevent infinite loops with model call limits
            ModelCallLimitMiddleware(
                thread_limit=20,  # Max 20 calls per thread (across runs)
                run_limit=5,     # Max 5 calls per run (single invocation)
                exit_behavior="end"  # Graceful termination when limit reached
            ),
            # Add error handling
            *create_simple_error_handler()
        ]
    )
    
    return chatbot_agent


# Initialize FastAPI app
app = FastAPI(
    title="AI Chatbot API",
    description="A REST API for an AI chatbot using LangChain create_agent",
    version="1.0.0"
)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "AI Chatbot API",
        "description": "A REST API for an AI chatbot using LangChain create_agent",
        "version": "1.0.0",
        "endpoints": {
            "chat": "/chat - POST endpoint to chat with the bot",
            "health": "/health - GET endpoint to check API health"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "message": "API is running"}


@app.post("/chat", response_model=ChatResponse)
async def chat_with_bot(request: ChatRequest):
    """
    Chat endpoint that processes user messages and returns bot responses.
    
    Args:
        request: ChatRequest containing the user message and optional user info
        
    Returns:
        ChatResponse with the bot's response and metadata
    """
    start_time = time.time()
    
    # Log the incoming request
    log_api_request(
        endpoint="/chat",
        method="POST",
        user_id=request.user_id,
        request_data={"message": request.message[:100] + "..." if len(request.message) > 100 else request.message}
    )
    
    try:
        # Get or create the chatbot agent with playbook enhancement
        agent = create_chatbot(request.message)
        
        # Configuration for the conversation with reasonable recursion limit
        config = {
            "configurable": {
                "thread_id": f"user_{request.user_id}"
            },
            "recursion_limit": 25  # Standard limit with ModelCallLimitMiddleware protection
        }
        context = Context(user_id=request.user_id, user_name=request.user_name)
        
        # Log the model call attempt
        print(f"Attempting to invoke agent for user: {request.user_id}")
        
        # Get response from the agent with timeout and fallback
        try:
            response = agent.invoke(
                {"messages": [{"role": "user", "content": request.message}]},
                config=config,
                context=context
            )
        except Exception as agent_error:
            # If agent fails due to recursion or other issues, provide a fallback response
            if "recursion limit" in str(agent_error).lower():
                log_recursion_limit(
                    limit=10,
                    current_iteration=10,
                    context=f"User: {request.user_id}, Message: {request.message[:50]}..."
                )
                
                # Create a fallback response based on the question type
                fallback_response = _get_fallback_response(request.message)
                response = {
                    "structured_response": ResponseFormat(
                        response=fallback_response,
                        confidence="low",
                        tools_used="fallback_response"
                    )
                }
            else:
                raise agent_error
        
        # Generate feedback ID for tracking
        feedback_id = create_feedback_id()
        
        # Extract response data
        if 'structured_response' in response:
            structured_resp = response['structured_response']
            response_text = structured_resp.response
            tools_used = structured_resp.tools_used
            confidence = structured_resp.confidence
        else:
            response_text = str(response)
            tools_used = None
            confidence = "medium"
        
        # Store chat data for feedback linking
        chat_storage.store_chat_data(
            feedback_id=feedback_id,
            user_id=request.user_id,
            user_name=request.user_name,
            question=request.message,
            model_response=response_text,
            tools_used=tools_used,
            confidence=confidence
        )
        
        # Log the successful interaction
        log_chat_interaction(
            user_id=request.user_id,
            question=request.message,
            response=response_text,
            feedback_id=feedback_id,
            tools_used=tools_used
        )
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log successful response
        log_api_response(
            endpoint="/chat",
            status_code=200,
            response_data={"feedback_id": feedback_id, "confidence": confidence},
            duration=duration
        )
        
        return ChatResponse(
            response=response_text,
            confidence=confidence,
            tools_used=tools_used,
            success=True,
            feedback_id=feedback_id
        )
            
    except Exception as e:
        # Log the error with full traceback
        error_context = f"Chat request failed for user {request.user_id}"
        log_error(
            error=e,
            context=error_context,
            additional_info={
                "user_id": request.user_id,
                "message": request.message,
                "traceback": traceback.format_exc()
            }
        )
        
        # Check if it's a recursion limit error
        if "recursion limit" in str(e).lower():
            log_recursion_limit(
                limit=25,  # Default limit
                current_iteration=25,
                context=f"User: {request.user_id}, Message: {request.message[:50]}..."
            )
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log failed response
        log_api_response(
            endpoint="/chat",
            status_code=500,
            response_data={"error": str(e)},
            duration=duration
        )
        
        raise HTTPException(
            status_code=500,
            detail=f"Error processing chat request: {str(e)}"
        )


@app.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest):
    """
    Submit feedback for a chatbot response.
    
    Args:
        request: FeedbackRequest containing feedback data
        
    Returns:
        FeedbackResponse with success status
    """
    start_time = time.time()
    
    # Log the incoming feedback request
    log_api_request(
        endpoint="/feedback",
        method="POST",
        user_id="unknown",  # Could be improved with proper user identification
        request_data={
            "feedback_id": request.feedback_id,
            "feedback_type": request.feedback_type,
            "rating": request.rating
        }
    )
    
    try:
        # Retrieve original chat data
        chat_data = chat_storage.get_chat_data(request.feedback_id)
        
        if not chat_data:
            raise HTTPException(
                status_code=404,
                detail=f"Chat data not found for feedback ID: {request.feedback_id}"
            )
        
        # Create feedback data object with original chat information
        feedback = FeedbackData(
            feedback_id=request.feedback_id,
            user_id=chat_data.get('user_id', 'unknown'),
            question=chat_data.get('question', ''),
            model_response=chat_data.get('model_response', ''),
            user_feedback=request.user_feedback,
            feedback_type=request.feedback_type,
            rating=request.rating,
            additional_notes=request.additional_notes,
            session_id=chat_data.get('user_id', 'unknown')
        )
        
        # Save feedback
        success = feedback_manager.save_feedback(feedback)
        
        # Log the feedback submission
        log_feedback(
            feedback_id=request.feedback_id,
            user_id="unknown",
            feedback_type=request.feedback_type,
            rating=request.rating
        )
        
        # 🚀 AUTOMATICALLY TRIGGER ACE PIPELINE
        print(f"🔄 Triggering ACE pipeline for feedback: {request.feedback_id}")
        try:
            ace_result = ace_pipeline.process_feedback(request.feedback_id)
            print(f"✅ ACE pipeline completed: {ace_result}")
        except Exception as ace_error:
            print(f"⚠️ ACE pipeline failed: {ace_error}")
            # Don't fail the feedback submission if ACE fails
        
        # Calculate duration
        duration = time.time() - start_time
        
        if success:
            # Log successful response
            log_api_response(
                endpoint="/feedback",
                status_code=200,
                response_data={"success": True, "feedback_id": request.feedback_id},
                duration=duration
            )
            
            return FeedbackResponse(
                success=True,
                message="Feedback submitted successfully and ACE pipeline triggered",
                feedback_id=request.feedback_id
            )
        else:
            # Log failed response
            log_api_response(
                endpoint="/feedback",
                status_code=500,
                response_data={"success": False, "error": "Failed to save feedback"},
                duration=duration
            )
            
            return FeedbackResponse(
                success=False,
                message="Failed to save feedback"
            )
            
    except Exception as e:
        # Log the error
        log_error(
            error=e,
            context="Feedback submission failed",
            additional_info={
                "feedback_id": request.feedback_id,
                "feedback_type": request.feedback_type,
                "traceback": traceback.format_exc()
            }
        )
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log failed response
        log_api_response(
            endpoint="/feedback",
            status_code=500,
            response_data={"error": str(e)},
            duration=duration
        )
        
        raise HTTPException(
            status_code=500,
            detail=f"Error processing feedback: {str(e)}"
        )


@app.get("/feedback/analytics")
async def get_feedback_analytics():
    """Get feedback analytics and insights."""
    try:
        analytics = feedback_manager.generate_analytics()
        return analytics
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating analytics: {str(e)}"
        )


@app.get("/feedback/user/{user_id}")
async def get_user_feedback(user_id: str):
    """Get feedback for a specific user."""
    try:
        feedback_list = feedback_manager.get_feedback_by_user(user_id)
        return {
            "user_id": user_id,
            "total_feedback": len(feedback_list),
            "feedback": [
                {
                    "feedback_id": f.feedback_id,
                    "question": f.question,
                    "user_feedback": f.user_feedback,
                    "feedback_type": f.feedback_type,
                    "rating": f.rating,
                    "timestamp": f.timestamp
                }
                for f in feedback_list
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving user feedback: {str(e)}"
        )


@app.get("/feedback/improvements")
async def get_improvement_suggestions():
    """Get improvement suggestions from feedback."""
    try:
        suggestions = feedback_manager.get_improvement_suggestions()
        return {
            "total_suggestions": len(suggestions),
            "suggestions": suggestions
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving improvement suggestions: {str(e)}"
        )


@app.get("/chat/{feedback_id}")
async def get_chat_data(feedback_id: str):
    """Get original chat data by feedback ID."""
    try:
        chat_data = chat_storage.get_chat_data(feedback_id)
        
        if not chat_data:
            raise HTTPException(
                status_code=404,
                detail=f"Chat data not found for feedback ID: {feedback_id}"
            )
        
        return {
            "feedback_id": feedback_id,
            "user_id": chat_data.get('user_id'),
            "user_name": chat_data.get('user_name'),
            "question": chat_data.get('question'),
            "model_response": chat_data.get('model_response'),
            "tools_used": chat_data.get('tools_used'),
            "confidence": chat_data.get('confidence'),
            "timestamp": chat_data.get('timestamp'),
            "created_at": chat_data.get('created_at')
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving chat data: {str(e)}"
        )


@app.get("/chat/user/{user_id}")
async def get_user_chats(user_id: str):
    """Get all chat data for a specific user."""
    try:
        user_chats = chat_storage.get_user_chats(user_id)
        return {
            "user_id": user_id,
            "total_chats": len(user_chats),
            "chats": user_chats
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving user chats: {str(e)}"
        )


# ACE Framework Endpoints

@app.get("/playbook")
async def get_playbook():
    """View current playbook."""
    try:
        stats = playbook_manager.get_stats()
        return {
            "success": True,
            "playbook_stats": stats,
            "message": "Playbook retrieved successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving playbook: {str(e)}")


@app.get("/playbook/bullets/{bullet_id}")
async def get_bullet(bullet_id: str):
    """Get specific bullet by ID."""
    try:
        bullet = playbook_manager.get_bullet(bullet_id)
        if not bullet:
            raise HTTPException(status_code=404, detail=f"Bullet {bullet_id} not found")
        
        return {
            "success": True,
            "bullet": bullet.to_dict(),
            "message": "Bullet retrieved successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving bullet: {str(e)}")


@app.get("/playbook/search")
async def search_playbook(query: str, top_k: int = 10):
    """Semantic search playbook."""
    try:
        relevant_bullets = playbook_manager.retrieve_relevant(query, top_k=top_k)
        return {
            "success": True,
            "query": query,
            "bullets": [bullet.to_dict() for bullet in relevant_bullets],
            "total_found": len(relevant_bullets),
            "message": "Search completed successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching playbook: {str(e)}")


@app.post("/playbook/trigger-update")
async def trigger_ace_update(feedback_id: str = None):
    """Manually trigger ACE update cycle for specific feedback."""
    try:
        result = await ace_pipeline.trigger_ace_update(feedback_id)
        return {
            "success": result["success"],
            "feedback_id": result["feedback_id"],
            "insights_generated": result["insights_generated"],
            "bullets_added": result["bullets_added"],
            "bullets_updated": result["bullets_updated"],
            "processing_time": result["processing_time"],
            "error_message": result["error_message"],
            "message": "ACE update triggered successfully" if result["success"] else "ACE update failed"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error triggering ACE update: {str(e)}")


@app.get("/playbook/stats")
async def get_playbook_stats():
    """Get playbook statistics."""
    try:
        stats = playbook_manager.get_stats()
        processing_stats = ace_pipeline.get_processing_stats()
        
        return {
            "success": True,
            "playbook_stats": stats,
            "processing_stats": processing_stats,
            "message": "Statistics retrieved successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving statistics: {str(e)}")


@app.post("/playbook/process-all")
async def process_all_pending():
    """Process all pending feedback through ACE pipeline."""
    try:
        results = await ace_pipeline.process_pending_feedback()
        
        total_processed = len(results)
        successful = len([r for r in results if r.success])
        total_bullets_added = sum(r.bullets_added for r in results)
        total_bullets_updated = sum(r.bullets_updated for r in results)
        
        return {
            "success": True,
            "total_processed": total_processed,
            "successful": successful,
            "failed": total_processed - successful,
            "total_bullets_added": total_bullets_added,
            "total_bullets_updated": total_bullets_updated,
            "results": [
                {
                    "feedback_id": r.feedback_id,
                    "success": r.success,
                    "bullets_added": r.bullets_added,
                    "bullets_updated": r.bullets_updated,
                    "processing_time": r.processing_time,
                    "error_message": r.error_message
                }
                for r in results
            ],
            "message": f"Processed {total_processed} feedback items"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing pending feedback: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("fastapi_chatbot:app", host="0.0.0.0", port=8000, reload=True)
