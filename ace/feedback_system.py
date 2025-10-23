"""
Feedback System for Chatbot
Handles user feedback collection and storage for model improvement.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class FeedbackData:
    """Data structure for storing feedback."""
    feedback_id: str
    user_id: str
    question: str
    model_response: str
    user_feedback: str
    feedback_type: str  # "correct", "incorrect", "partially_correct", "improvement_suggestion"
    rating: Optional[int] = None  # 1-5 scale
    timestamp: str = ""
    session_id: Optional[str] = None
    additional_notes: Optional[str] = None


class FeedbackManager:
    """Manages feedback collection and storage."""
    
    def __init__(self, feedback_dir: str = "feedback_data"):
        self.feedback_dir = Path(feedback_dir)
        self.feedback_dir.mkdir(exist_ok=True)
        
        # Create subdirectories for organization
        (self.feedback_dir / "raw").mkdir(exist_ok=True)
        (self.feedback_dir / "processed").mkdir(exist_ok=True)
        (self.feedback_dir / "analytics").mkdir(exist_ok=True)
    
    def save_feedback(self, feedback: FeedbackData) -> bool:
        """Save feedback data to file."""
        try:
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"feedback_{feedback.feedback_id}_{timestamp}.json"
            filepath = self.feedback_dir / "raw" / filename
            
            # Add timestamp if not set
            if not feedback.timestamp:
                feedback.timestamp = datetime.now().isoformat()
            
            # Save to file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(asdict(feedback), f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"Error saving feedback: {e}")
            return False
    
    def get_feedback_by_user(self, user_id: str) -> List[FeedbackData]:
        """Get all feedback for a specific user."""
        feedback_list = []
        raw_dir = self.feedback_dir / "raw"
        
        for file_path in raw_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data.get('user_id') == user_id:
                        feedback_list.append(FeedbackData(**data))
            except Exception as e:
                print(f"Error reading feedback file {file_path}: {e}")
        
        return sorted(feedback_list, key=lambda x: x.timestamp, reverse=True)
    
    def get_all_feedback(self) -> List[FeedbackData]:
        """Get all feedback data."""
        feedback_list = []
        raw_dir = self.feedback_dir / "raw"
        
        for file_path in raw_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    feedback_list.append(FeedbackData(**data))
            except Exception as e:
                print(f"Error reading feedback file {file_path}: {e}")
        
        return sorted(feedback_list, key=lambda x: x.timestamp, reverse=True)
    
    def get_feedback(self, feedback_id: str) -> Optional[FeedbackData]:
        """Get specific feedback by ID."""
        all_feedback = self.get_all_feedback()
        for feedback in all_feedback:
            if feedback.feedback_id == feedback_id:
                return feedback
        return None
    
    def generate_analytics(self) -> Dict[str, Any]:
        """Generate analytics from feedback data."""
        all_feedback = self.get_all_feedback()
        
        if not all_feedback:
            return {"message": "No feedback data available"}
        
        # Basic analytics
        total_feedback = len(all_feedback)
        feedback_types = {}
        ratings = []
        user_counts = {}
        
        for feedback in all_feedback:
            # Count feedback types
            feedback_types[feedback.feedback_type] = feedback_types.get(feedback.feedback_type, 0) + 1
            
            # Collect ratings
            if feedback.rating:
                ratings.append(feedback.rating)
            
            # Count by user
            user_counts[feedback.user_id] = user_counts.get(feedback.user_id, 0) + 1
        
        # Calculate average rating
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        
        analytics = {
            "total_feedback": total_feedback,
            "feedback_types": feedback_types,
            "average_rating": round(avg_rating, 2),
            "user_feedback_counts": user_counts,
            "recent_feedback": [
                {
                    "feedback_id": f.feedback_id,
                    "user_id": f.user_id,
                    "question": f.question[:100] + "..." if len(f.question) > 100 else f.question,
                    "feedback_type": f.feedback_type,
                    "rating": f.rating,
                    "timestamp": f.timestamp
                }
                for f in all_feedback[:10]  # Last 10 feedback entries
            ]
        }
        
        # Save analytics
        analytics_file = self.feedback_dir / "analytics" / "feedback_analytics.json"
        with open(analytics_file, 'w', encoding='utf-8') as f:
            json.dump(analytics, f, indent=2, ensure_ascii=False)
        
        return analytics
    
    def get_improvement_suggestions(self) -> List[Dict[str, str]]:
        """Get improvement suggestions from feedback."""
        all_feedback = self.get_all_feedback()
        suggestions = []
        
        for feedback in all_feedback:
            if feedback.feedback_type in ["incorrect", "partially_correct", "improvement_suggestion"]:
                suggestions.append({
                    "feedback_id": feedback.feedback_id,
                    "question": feedback.question,
                    "model_response": feedback.model_response,
                    "user_feedback": feedback.user_feedback,
                    "additional_notes": feedback.additional_notes,
                    "timestamp": feedback.timestamp
                })
        
        return suggestions


def create_feedback_id() -> str:
    """Generate a unique feedback ID."""
    import uuid
    return str(uuid.uuid4())[:8]


# Example usage and testing
if __name__ == "__main__":
    # Test the feedback system
    feedback_manager = FeedbackManager()
    
    # Create sample feedback
    sample_feedback = FeedbackData(
        feedback_id=create_feedback_id(),
        user_id="test_user_1",
        question="What is machine learning?",
        model_response="Machine learning is a subset of AI...",
        user_feedback="The response was too technical and didn't explain the basics clearly.",
        feedback_type="improvement_suggestion",
        rating=3,
        session_id="session_123",
        additional_notes="User is a beginner and needs simpler explanations."
    )
    
    # Save feedback
    success = feedback_manager.save_feedback(sample_feedback)
    print(f"Feedback saved: {success}")
    
    # Generate analytics
    analytics = feedback_manager.generate_analytics()
    print("Analytics:", json.dumps(analytics, indent=2))
