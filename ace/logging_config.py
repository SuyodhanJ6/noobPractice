"""
Logging Configuration for Chatbot
Handles all logging for the chatbot system including API calls, errors, and debugging.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


class ChatbotLogger:
    """Centralized logging system for the chatbot."""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Create subdirectories for different log types
        (self.log_dir / "api").mkdir(exist_ok=True)
        (self.log_dir / "errors").mkdir(exist_ok=True)
        (self.log_dir / "debug").mkdir(exist_ok=True)
        (self.log_dir / "feedback").mkdir(exist_ok=True)
        
        self._setup_loggers()
    
    def _setup_loggers(self):
        """Setup different loggers for different purposes."""
        
        # Main API logger
        self.api_logger = self._create_logger(
            name="chatbot_api",
            log_file=self.log_dir / "api" / "api.log",
            level=logging.INFO
        )
        
        # Error logger
        self.error_logger = self._create_logger(
            name="chatbot_errors",
            log_file=self.log_dir / "errors" / "errors.log",
            level=logging.ERROR
        )
        
        # Debug logger
        self.debug_logger = self._create_logger(
            name="chatbot_debug",
            log_file=self.log_dir / "debug" / "debug.log",
            level=logging.DEBUG
        )
        
        # Feedback logger
        self.feedback_logger = self._create_logger(
            name="chatbot_feedback",
            log_file=self.log_dir / "feedback" / "feedback.log",
            level=logging.INFO
        )
    
    def _create_logger(self, name: str, log_file: Path, level: int) -> logging.Logger:
        """Create a logger with file and console handlers."""
        logger = logging.getLogger(name)
        logger.setLevel(level)
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # File handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def log_api_request(self, endpoint: str, method: str, user_id: str, request_data: dict):
        """Log API requests."""
        self.api_logger.info(
            f"API Request - {method} {endpoint} - User: {user_id} - Data: {request_data}"
        )
    
    def log_api_response(self, endpoint: str, status_code: int, response_data: dict, duration: float):
        """Log API responses."""
        self.api_logger.info(
            f"API Response - {endpoint} - Status: {status_code} - Duration: {duration:.2f}s - Response: {response_data}"
        )
    
    def log_error(self, error: Exception, context: str = "", additional_info: dict = None):
        """Log errors with context."""
        error_info = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
            "timestamp": datetime.now().isoformat()
        }
        
        if additional_info:
            error_info.update(additional_info)
        
        self.error_logger.error(f"Error occurred: {error_info}")
        
        # Also log to debug for more details
        self.debug_logger.debug(f"Full error details: {error_info}")
    
    def log_chat_interaction(self, user_id: str, question: str, response: str, feedback_id: str, tools_used: str = None):
        """Log chat interactions."""
        self.api_logger.info(
            f"Chat Interaction - User: {user_id} - Question: {question[:100]}... - "
            f"Response: {response[:100]}... - Feedback ID: {feedback_id} - Tools: {tools_used}"
        )
    
    def log_feedback(self, feedback_id: str, user_id: str, feedback_type: str, rating: int = None):
        """Log feedback submissions."""
        self.feedback_logger.info(
            f"Feedback Submitted - ID: {feedback_id} - User: {user_id} - "
            f"Type: {feedback_type} - Rating: {rating}"
        )
    
    def log_model_call(self, model_name: str, prompt: str, response: str, tokens_used: int = None):
        """Log model API calls."""
        self.debug_logger.debug(
            f"Model Call - Model: {model_name} - Prompt: {prompt[:200]}... - "
            f"Response: {response[:200]}... - Tokens: {tokens_used}"
        )
    
    def log_tool_usage(self, tool_name: str, input_data: dict, output: str, execution_time: float):
        """Log tool usage."""
        self.debug_logger.debug(
            f"Tool Usage - Tool: {tool_name} - Input: {input_data} - "
            f"Output: {output[:100]}... - Time: {execution_time:.2f}s"
        )
    
    def log_recursion_limit(self, limit: int, current_iteration: int, context: str):
        """Log recursion limit issues."""
        self.error_logger.error(
            f"Recursion Limit Reached - Limit: {limit} - Current: {current_iteration} - Context: {context}"
        )
    
    def get_log_files(self) -> dict:
        """Get list of all log files."""
        log_files = {}
        for log_type in ["api", "errors", "debug", "feedback"]:
            log_dir = self.log_dir / log_type
            if log_dir.exists():
                log_files[log_type] = [f.name for f in log_dir.glob("*.log")]
        return log_files
    
    def clear_old_logs(self, days: int = 7):
        """Clear logs older than specified days."""
        import time
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        
        for log_type in ["api", "errors", "debug", "feedback"]:
            log_dir = self.log_dir / log_type
            if log_dir.exists():
                for log_file in log_dir.glob("*.log"):
                    if log_file.stat().st_mtime < cutoff_time:
                        log_file.unlink()
                        self.api_logger.info(f"Cleared old log file: {log_file}")


# Global logger instance
logger = ChatbotLogger()


# Convenience functions
def log_api_request(endpoint: str, method: str, user_id: str, request_data: dict):
    """Log API request."""
    logger.log_api_request(endpoint, method, user_id, request_data)


def log_api_response(endpoint: str, status_code: int, response_data: dict, duration: float):
    """Log API response."""
    logger.log_api_response(endpoint, status_code, response_data, duration)


def log_error(error: Exception, context: str = "", additional_info: dict = None):
    """Log error."""
    logger.log_error(error, context, additional_info)


def log_chat_interaction(user_id: str, question: str, response: str, feedback_id: str, tools_used: str = None):
    """Log chat interaction."""
    logger.log_chat_interaction(user_id, question, response, feedback_id, tools_used)


def log_feedback(feedback_id: str, user_id: str, feedback_type: str, rating: int = None):
    """Log feedback."""
    logger.log_feedback(feedback_id, user_id, feedback_type, rating)


def log_model_call(model_name: str, prompt: str, response: str, tokens_used: int = None):
    """Log model call."""
    logger.log_model_call(model_name, prompt, response, tokens_used)


def log_tool_usage(tool_name: str, input_data: dict, output: str, execution_time: float):
    """Log tool usage."""
    logger.log_tool_usage(tool_name, input_data, output, execution_time)


def log_recursion_limit(limit: int, current_iteration: int, context: str):
    """Log recursion limit."""
    logger.log_recursion_limit(limit, current_iteration, context)
