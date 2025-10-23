"""
Simplified FastAPI Chatbot with Automatic ACE Pipeline
- Only essential endpoints: /chat, /feedback
- ACE pipeline runs automatically when feedback is submitted
- Clean and minimal API
"""

import os
import time
import traceback
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our modules
from chatbot import init_chat_model, create_agent, search_web, calculate, get_time, get_user_info, explain_concept, Context, ResponseFormat, checkpointer
from feedback_system import FeedbackManager, FeedbackData, create_feedback_id
from chat_storage import ChatStorage
from logging_config import log_api_request, log_chat_interaction, log_api_response, log_feedback, log_error, log_recursion_limit
from error_handling_middleware import create_simple_error_handler
from playbook_manager import playbook_manager
from ace_pipeline import ace_pipeline
from langchain_core.middleware import ModelCallLimitMiddleware

# Initialize FastAPI app
app = FastAPI(
    title="ACE Chatbot API",
    description="AI Chatbot with Automatic ACE (Agentic Context Engineering) Pipeline",
    version="1.0.0"
)

# Global instances
feedback_manager = FeedbackManager()
chat_storage = ChatStorage()
chatbot_agent = None

# Pydantic models
class ChatRequest(BaseModel):
    message: str
    user_id: str
    user_name: str

class ChatResponse(BaseModel):
    response: str
    confidence: str
    tools_used: Optional[str] = None
    success: bool
    feedback_id: str

class FeedbackRequest(BaseModel):
    feedback_id: str
    user_feedback: str
    feedback_type: str
    rating: int
    additional_notes: Optional[str] = None

class FeedbackResponse(BaseModel):
    success: bool
    message: str
    feedback_id: str

# Base system prompt
BASE_SYSTEM_PROMPT = """You are a helpful AI assistant chatbot with access to a curated playbook of strategies.

Your goal is to provide accurate, helpful responses to user questions. You have access to various tools and a playbook of proven strategies.

When responding:
1. Be accurate and factual
2. Use tools when appropriate
3. Reference playbook strategies when relevant
4. Provide clear, concise answers
5. If you're unsure, say so rather than guessing

Remember: You have access to a playbook of strategies that can help you provide better responses."""

def get_enhanced_system_prompt(user_question: str) -> str:
    """Get system prompt enhanced with relevant playbook bullets"""
    try:
        # Get relevant bullets from playbook
        relevant_bullets = playbook_manager.retrieve_relevant(user_question, top_k=10)
        
        if not relevant_bullets:
            return BASE_SYSTEM_PROMPT
        
        # Add playbook section to prompt
        playbook_section = "\n\nPLAYBOOK (Relevant Strategies):\n"
        for bullet in relevant_bullets:
            playbook_section += f"- {bullet.content}\n"
        
        enhanced_prompt = BASE_SYSTEM_PROMPT + playbook_section
        return enhanced_prompt
        
    except Exception as e:
        print(f"Error getting enhanced prompt: {e}")
        return BASE_SYSTEM_PROMPT

def create_chatbot(user_question: str = ""):
    """Create chatbot agent with enhanced prompt"""
    global chatbot_agent
    
    model = init_chat_model(
        "openai:gpt-4o-mini",
        temperature=0.7
    )
    
    # Get enhanced system prompt with relevant playbook bullets
    enhanced_prompt = get_enhanced_system_prompt(user_question)
    
    chatbot_agent = create_agent(
        model=model,
        debug=True,
        system_prompt=enhanced_prompt,
        tools=[search_web, calculate, get_time, get_user_info, explain_concept],
        context_schema=Context,
        response_format=ResponseFormat,
        checkpointer=checkpointer,
        middleware=[
            ModelCallLimitMiddleware(
                thread_limit=20,
                run_limit=5,
                exit_behavior="end"
            ),
            *create_simple_error_handler()
        ]
    )
    return chatbot_agent

def _get_fallback_response(message: str) -> str:
    """Provide a fallback response when recursion limit is reached"""
    return f"""I apologize, but I encountered a technical issue while processing your question: "{message}".

This sometimes happens with complex queries. Please try:
1. Breaking your question into smaller parts
2. Rephrasing your question more simply
3. Asking a different but related question

I'm here to help, so please feel free to try again!"""

# Routes
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "ACE Chatbot API is running!",
        "endpoints": {
            "chat": "/chat",
            "feedback": "/feedback",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": time.time()}

@app.post("/chat", response_model=ChatResponse)
async def chat_with_bot(request: ChatRequest):
    """
    Chat with the AI assistant.
    
    Args:
        request: ChatRequest containing message and user info
        
    Returns:
        ChatResponse with AI response and feedback ID
    """
    start_time = time.time()
    
    # Log the incoming request
    log_api_request(
        endpoint="/chat",
        method="POST",
        user_id=request.user_id,
        request_data={"message": request.message}
    )
    
    try:
        # Create chatbot with enhanced prompt for this specific question
        agent = create_chatbot(request.message)
        
        # Generate feedback ID for this interaction
        feedback_id = create_feedback_id()
        
        # Store chat data for potential feedback
        chat_storage.store_chat_data(
            feedback_id=feedback_id,
            user_id=request.user_id,
            user_name=request.user_name,
            question=request.message,
            model_response="",  # Will be updated after response
            timestamp=time.time()
        )
        
        # Log chat interaction start
        log_chat_interaction(
            feedback_id=feedback_id,
            user_id=request.user_id,
            message=request.message
        )
        
        print(f"Attempting to invoke agent for user: {request.user_id}")
        
        # Invoke agent with recursion limit
        response = agent.invoke(
            {"messages": [("user", request.message)]},
            config={"recursion_limit": 25}
        )
        
        # Extract response content
        if hasattr(response, 'content'):
            response_content = response.content
        else:
            response_content = str(response)
        
        # Update stored chat data with actual response
        chat_storage.update_chat_response(feedback_id, response_content)
        
        # Log successful chat interaction
        log_chat_interaction(
            feedback_id=feedback_id,
            user_id=request.user_id,
            message=request.message,
            response=response_content,
            success=True
        )
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log successful response
        log_api_response(
            endpoint="/chat",
            status_code=200,
            response_data={"response": response_content[:100] + "..."},
            duration=duration
        )
        
        return ChatResponse(
            response=response_content,
            confidence="high",
            tools_used=None,
            success=True,
            feedback_id=feedback_id
        )
        
    except Exception as e:
        # Check if it's a recursion limit error
        if "recursion limit" in str(e).lower():
            log_recursion_limit(
                limit=25,
                current_iteration=25,
                context=f"User: {request.user_id}, Message: {request.message[:50]}..."
            )
            
            # Provide fallback response
            fallback_response = _get_fallback_response(request.message)
            
            # Update stored chat data with fallback response
            chat_storage.update_chat_response(feedback_id, fallback_response)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log fallback response
            log_api_response(
                endpoint="/chat",
                status_code=200,
                response_data={"response": "fallback_response"},
                duration=duration
            )
            
            return ChatResponse(
                response=fallback_response,
                confidence="low",
                tools_used=None,
                success=True,
                feedback_id=feedback_id
            )
        
        # Log the error
        log_error(
            error=e,
            context="Chat request failed",
            additional_info={
                "user_id": request.user_id,
                "message": request.message,
                "traceback": traceback.format_exc()
            }
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
    Automatically triggers ACE pipeline for learning.
    
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
        user_id="unknown",
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
