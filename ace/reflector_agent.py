"""
Reflector Agent for ACE Framework
Analyzes user feedback and extracts actionable insights
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from langchain.chat_models import init_chat_model
from playbook_manager import playbook_manager


@dataclass
class ReflectionInsight:
    """Structured insight extracted from feedback analysis"""
    error_identification: str
    root_cause_analysis: str
    correct_approach: str
    key_insight: str
    bullet_tags: List[Dict[str, str]]  # [{"id": "ctx-123", "tag": "helpful"}]
    confidence: float = 0.0


class ReflectorAgent:
    """Analyzes feedback and extracts insights for playbook improvement"""
    
    def __init__(self):
        self.model = init_chat_model("openai:gpt-4o-mini", temperature=0.3)
        self.reflections_dir = "ace/reflections"
        
        # Create reflections directory
        os.makedirs(self.reflections_dir, exist_ok=True)
    
    def analyze_feedback(self, chat_data: Dict[str, Any], feedback_data) -> ReflectionInsight:
        """Analyze user feedback and extract insights"""
        
        # Extract data
        question = chat_data.get("question", "")
        model_response = chat_data.get("model_response", "")
        user_feedback = feedback_data.user_feedback
        feedback_type = feedback_data.feedback_type
        rating = feedback_data.rating
        
        print(f"   🔍 Reflector analyzing feedback:")
        print(f"      - Question: {question[:50]}...")
        print(f"      - Feedback type: {feedback_type}")
        print(f"      - Rating: {rating}/5")
        print(f"      - User feedback: {user_feedback[:100]}...")
        
        # Generate reflection using LLM
        print(f"   🤖 Calling LLM for reflection analysis...")
        reflection = self._generate_reflection(
            question=question,
            model_response=model_response,
            user_feedback=user_feedback,
            feedback_type=feedback_type,
            rating=rating
        )
        
        # Save reflection for debugging
        self._save_reflection(feedback_data.feedback_id, reflection)
        
        return reflection
    
    def _generate_reflection(self, question: str, model_response: str, user_feedback: str, 
                           feedback_type: str, rating: int) -> ReflectionInsight:
        """Use LLM to analyze feedback and extract insights"""
        
        prompt = f"""Analyze why this response received feedback and extract actionable insights.

QUESTION: {question}

MODEL RESPONSE: {model_response}

USER FEEDBACK: {user_feedback}
FEEDBACK TYPE: {feedback_type}
RATING: {rating}/5

Based on the user's feedback, analyze and provide:

1. ERROR IDENTIFICATION: What specifically was wrong or missing in the response?
2. ROOT CAUSE ANALYSIS: Why did the model make this mistake? What was the underlying issue?
3. CORRECT APPROACH: What should have been done instead?
4. KEY INSIGHT: What actionable strategy should be added to the playbook to prevent this in future?

IMPORTANT: The key_insight should be a CLEAR, ACTIONABLE strategy in this format:
- For SUCCESS patterns: "When answering [question type], use this approach: [specific steps]"
- For ERROR patterns: "When [situation], avoid [mistake] and instead [correct approach]"
- Use numbered lists for multiple steps: "1. First step, 2. Second step, 3. Third step"
- Be specific and practical, NOT technical object data

Output your analysis as JSON with these exact fields:
{{
    "error_identification": "Specific description of what was wrong",
    "root_cause_analysis": "Why this mistake happened",
    "correct_approach": "What should have been done",
    "key_insight": "Clear, actionable strategy for the playbook (human-readable, not technical data)",
    "confidence": 0.8
}}

Be specific and actionable. The key_insight should be a concrete, human-readable strategy that can be added to a playbook."""

        try:
            print(f"      📤 Sending prompt to LLM (length: {len(prompt)} chars)")
            response = self.model.invoke([
                {"role": "system", "content": "You are an expert at analyzing AI model failures and extracting actionable insights for improvement."},
                {"role": "user", "content": prompt}
            ])
            
            # Parse JSON response
            content = response.content.strip()
            print(f"      📥 Received response (length: {len(content)} chars)")
            
            # Try to extract JSON from response
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                content = content[json_start:json_end].strip()
            elif "```" in content:
                json_start = content.find("```") + 3
                json_end = content.find("```", json_start)
                content = content[json_start:json_end].strip()
            
            # Parse JSON
            try:
                analysis = json.loads(content)
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                analysis = {
                    "error_identification": user_feedback,
                    "root_cause_analysis": "Unable to analyze automatically",
                    "correct_approach": "Review user feedback for guidance",
                    "key_insight": f"User feedback: {user_feedback}",
                    "confidence": 0.5
                }
            
            # Create ReflectionInsight object
            insight = ReflectionInsight(
                error_identification=analysis.get("error_identification", user_feedback),
                root_cause_analysis=analysis.get("root_cause_analysis", "Analysis failed"),
                correct_approach=analysis.get("correct_approach", "Manual review needed"),
                key_insight=analysis.get("key_insight", f"User feedback: {user_feedback}"),
                bullet_tags=[],  # Will be filled by Curator
                confidence=analysis.get("confidence", 0.5)
            )
            
            return insight
            
        except Exception as e:
            print(f"Error in reflection generation: {e}")
            # Return fallback insight
            return ReflectionInsight(
                error_identification=user_feedback,
                root_cause_analysis="Reflection generation failed",
                correct_approach="Manual review required",
                key_insight=f"User feedback: {user_feedback}",
                bullet_tags=[],
                confidence=0.3
            )
    
    def _save_reflection(self, feedback_id: str, reflection: ReflectionInsight):
        """Save reflection to file for debugging"""
        reflection_data = {
            "feedback_id": feedback_id,
            "timestamp": datetime.now().isoformat(),
            "error_identification": reflection.error_identification,
            "root_cause_analysis": reflection.root_cause_analysis,
            "correct_approach": reflection.correct_approach,
            "key_insight": reflection.key_insight,
            "confidence": reflection.confidence,
            "bullet_tags": reflection.bullet_tags
        }
        
        filename = f"reflection_{feedback_id}.json"
        filepath = os.path.join(self.reflections_dir, filename)
        
        try:
            with open(filepath, 'w') as f:
                json.dump(reflection_data, f, indent=2)
        except Exception as e:
            print(f"Error saving reflection: {e}")
    
    def extract_insights_from_success(self, question: str, model_response: str, 
                                    feedback_type: str, rating: int) -> ReflectionInsight:
        """Extract insights from positive feedback (what worked well)"""
        
        if rating >= 4:  # High rating
            insight_content = f"Successful response pattern: {model_response}"
            
            return ReflectionInsight(
                error_identification="No errors - successful response",
                root_cause_analysis="Response met user expectations",
                correct_approach="Continue using this approach",
                key_insight=f"When answering '{question}', use this successful pattern: {model_response}",
                bullet_tags=[],
                confidence=0.8
            )
        else:
            # Medium rating - partial success
            return ReflectionInsight(
                error_identification="Partially successful response",
                root_cause_analysis="Response had some value but could be improved",
                correct_approach="Build on what worked, improve what didn't",
                key_insight=f"Partial success pattern for '{question}': {model_response}",
                bullet_tags=[],
                confidence=0.6
            )


# Global reflector instance
reflector_agent = ReflectorAgent()
