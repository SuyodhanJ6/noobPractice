"""
Error Handling Middleware for Chatbot
Comprehensive error handling that prevents system crashes and provides graceful fallbacks.
"""

from typing import Any, Dict, Optional
from langchain.agents.middleware import wrap_tool_call
from langchain_core.messages import ToolMessage
from langchain.agents.middleware import AgentMiddleware
from langchain.agents import AgentState
from langgraph.runtime import Runtime
import traceback
import time
from logging_config import log_error, log_tool_usage


class RobustErrorHandlingMiddleware(AgentMiddleware):
    """Comprehensive error handling middleware that prevents system crashes."""
    
    def __init__(self, max_retries: int = 3, fallback_responses: Dict[str, str] = None):
        super().__init__()
        self.max_retries = max_retries
        self.fallback_responses = fallback_responses or {
            "calculate": "I'm having trouble with that calculation. Please try a simpler math problem.",
            "search_web": "I'm unable to search the web right now. Please try asking a different question.",
            "get_time": "I'm having trouble getting the current time. Please check your device's clock.",
            "get_user_info": "I'm unable to retrieve user information at the moment.",
            "explain_concept": "I'm having trouble explaining that concept right now. Please try rephrasing your question."
        }
    
    def wrap_tool_call(self, request, handler):
        """Wrap tool calls with comprehensive error handling."""
        tool_name = request.tool_call.get("name", "unknown_tool")
        start_time = time.time()
        
        try:
            # Attempt to execute the tool
            result = handler(request)
            
            # Log successful tool usage
            execution_time = time.time() - start_time
            log_tool_usage(
                tool_name=tool_name,
                input_data={"tool_call": request.tool_call},
                output=str(result)[:100] + "..." if len(str(result)) > 100 else str(result),
                execution_time=execution_time
            )
            
            return result
            
        except Exception as e:
            # Log the error
            log_error(
                error=e,
                context=f"Tool execution failed: {tool_name}",
                additional_info={
                    "tool_name": tool_name,
                    "tool_call": request.tool_call,
                    "traceback": traceback.format_exc()
                }
            )
            
            # Return a graceful error message
            error_message = self._get_error_message(tool_name, str(e))
            
            return ToolMessage(
                content=error_message,
                tool_call_id=request.tool_call["id"]
            )
    
    def _get_error_message(self, tool_name: str, error_details: str) -> str:
        """Generate appropriate error messages based on tool and error type."""
        
        # Check if we have a specific fallback for this tool
        if tool_name in self.fallback_responses:
            return self.fallback_responses[tool_name]
        
        # Handle specific error types
        if "division by zero" in error_details.lower():
            return "I can't divide by zero. Please provide a valid calculation."
        
        if "invalid expression" in error_details.lower():
            return "I couldn't understand that calculation. Please use numbers and basic operators (+, -, *, /)."
        
        if "timeout" in error_details.lower():
            return "The request timed out. Please try again with a simpler question."
        
        if "connection" in error_details.lower():
            return "I'm having trouble connecting to external services. Please try again later."
        
        if "permission" in error_details.lower() or "access" in error_details.lower():
            return "I don't have permission to access that information."
        
        # Generic fallback
        return f"I encountered an error while trying to help you. Please try rephrasing your question or ask something else."


@wrap_tool_call
def handle_tool_errors(request, handler):
    """Simple tool error handler that prevents crashes."""
    try:
        return handler(request)
    except Exception as e:
        # Log the error
        log_error(
            error=e,
            context="Tool execution error",
            additional_info={
                "tool_call": request.tool_call,
                "error_type": type(e).__name__
            }
        )
        
        # Return a user-friendly error message
        return ToolMessage(
            content=f"I'm sorry, I encountered an error while trying to help you. Please try rephrasing your question or ask something else.",
            tool_call_id=request.tool_call["id"]
        )


class CircuitBreakerMiddleware(AgentMiddleware):
    """Circuit breaker pattern to prevent cascading failures."""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        super().__init__()
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def wrap_tool_call(self, request, handler):
        """Implement circuit breaker pattern for tool calls."""
        
        # Check if circuit is open
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
            else:
                return ToolMessage(
                    content="I'm temporarily unavailable due to recent errors. Please try again in a moment.",
                    tool_call_id=request.tool_call["id"]
                )
        
        try:
            result = handler(request)
            
            # Reset on success
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
            
            return result
            
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            # Open circuit if threshold reached
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
            
            # Log the error
            log_error(
                error=e,
                context="Circuit breaker triggered",
                additional_info={
                    "failure_count": self.failure_count,
                    "state": self.state,
                    "tool_call": request.tool_call
                }
            )
            
            return ToolMessage(
                content="I'm experiencing some technical difficulties. Please try again later.",
                tool_call_id=request.tool_call["id"]
            )


class RetryMiddleware(AgentMiddleware):
    """Retry middleware with exponential backoff."""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
        super().__init__()
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    def wrap_tool_call(self, request, handler):
        """Retry tool calls with exponential backoff."""
        
        for attempt in range(self.max_retries + 1):
            try:
                return handler(request)
                
            except Exception as e:
                if attempt == self.max_retries:
                    # Final attempt failed
                    log_error(
                        error=e,
                        context=f"Tool call failed after {self.max_retries} retries",
                        additional_info={
                            "tool_call": request.tool_call,
                            "attempts": attempt + 1
                        }
                    )
                    
                    return ToolMessage(
                        content="I'm having persistent issues with this request. Please try a different approach.",
                        tool_call_id=request.tool_call["id"]
                    )
                
                # Calculate delay with exponential backoff
                delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                time.sleep(delay)
                
                log_error(
                    error=e,
                    context=f"Tool call failed, retrying in {delay}s (attempt {attempt + 1}/{self.max_retries})",
                    additional_info={
                        "tool_call": request.tool_call,
                        "attempt": attempt + 1,
                        "delay": delay
                    }
                )


class GracefulDegradationMiddleware(AgentMiddleware):
    """Middleware that provides graceful degradation when tools fail."""
    
    def __init__(self):
        super().__init__()
        self.failed_tools = set()
    
    def wrap_tool_call(self, request, handler):
        """Provide graceful degradation for failed tools."""
        tool_name = request.tool_call.get("name", "unknown")
        
        # If tool has failed before, provide alternative response
        if tool_name in self.failed_tools:
            return ToolMessage(
                content=self._get_alternative_response(tool_name),
                tool_call_id=request.tool_call["id"]
            )
        
        try:
            result = handler(request)
            return result
            
        except Exception as e:
            # Mark tool as failed
            self.failed_tools.add(tool_name)
            
            log_error(
                error=e,
                context=f"Tool {tool_name} failed, providing alternative",
                additional_info={
                    "tool_name": tool_name,
                    "tool_call": request.tool_call
                }
            )
            
            return ToolMessage(
                content=self._get_alternative_response(tool_name),
                tool_call_id=request.tool_call["id"]
            )
    
    def _get_alternative_response(self, tool_name: str) -> str:
        """Get alternative response when tool fails."""
        alternatives = {
            "calculate": "I'm having trouble with calculations right now. You might want to use a calculator for this.",
            "search_web": "I can't search the web at the moment, but I can try to help with general knowledge questions.",
            "get_time": "I can't get the current time right now. Please check your device's clock.",
            "get_user_info": "I'm unable to access user information at the moment.",
            "explain_concept": "I'm having trouble explaining concepts right now. You might want to search online for more information."
        }
        
        return alternatives.get(tool_name, "I'm having trouble with that request. Please try something else.")


# Combined middleware for comprehensive error handling
def create_error_handling_middleware():
    """Create a comprehensive error handling middleware stack."""
    return [
        RobustErrorHandlingMiddleware(),
        CircuitBreakerMiddleware(),
        RetryMiddleware(),
        GracefulDegradationMiddleware()
    ]


# Simple error handler for basic use cases
def create_simple_error_handler():
    """Create a simple error handler for basic use cases."""
    return [handle_tool_errors]
