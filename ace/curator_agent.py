"""
Curator Agent for ACE Framework
Manages playbook updates based on Reflector insights
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from playbook_manager import playbook_manager, Bullet
from reflector_agent import ReflectionInsight


@dataclass
class DeltaOperation:
    """Represents a single playbook update operation"""
    operation: str  # "ADD", "UPDATE", "DEDUPLICATE"
    bullet_id: Optional[str] = None
    content: Optional[str] = None
    section: Optional[str] = None
    helpful_increment: int = 0
    harmful_increment: int = 0


@dataclass
class DeltaUpdate:
    """Collection of operations to apply to playbook"""
    operations: List[DeltaOperation]
    timestamp: str
    source_feedback_id: str
    total_operations: int


class CuratorAgent:
    """Manages playbook updates based on Reflector insights"""
    
    def __init__(self):
        self.updates_dir = "ace/ace_updates"
        
        # Create updates directory
        os.makedirs(self.updates_dir, exist_ok=True)
    
    def process_insights(self, insight: ReflectionInsight, feedback_id: str) -> DeltaUpdate:
        """Process Reflector insights and create playbook delta"""
        
        print(f"   📚 Curator processing insights:")
        print(f"      - Key insight: {insight.key_insight[:100]}...")
        print(f"      - Confidence: {insight.confidence}")
        print(f"      - Error identification: {insight.error_identification[:100]}...")
        
        operations = []
        
        # Determine if this is a new insight or update to existing
        if insight.confidence > 0.5:  # Only process high-confidence insights
            print(f"      ✅ High confidence insight (>{0.5}), processing...")
            
            # Check if similar insight already exists
            similar_bullets = self._find_similar_bullets(insight.key_insight)
            
            if similar_bullets:
                # UPDATE existing bullet
                best_match = similar_bullets[0]
                print(f"      🔄 Found similar bullet: {best_match.id}")
                
                # Format content to ensure ACE compliance (for UPDATE path too)
                print(f"      🔧 CALLING FORMATTING FUNCTION (UPDATE PATH)...")
                formatted_content = self._format_bullet_content(insight.key_insight, insight)
                print(f"      🔧 FORMATTING FUNCTION COMPLETED (UPDATE PATH)")
                
                operations.append(DeltaOperation(
                    operation="UPDATE",
                    bullet_id=best_match.id,
                    content=formatted_content,  # Add formatted content to UPDATE
                    helpful_increment=1 if insight.confidence > 0.7 else 0,
                    harmful_increment=0
                ))
            else:
                # ADD new bullet
                section = self._determine_section(insight)
                print(f"      ➕ Creating new bullet in section: {section}")
                
                # Format content to ensure ACE compliance
                print(f"      🔧 CALLING FORMATTING FUNCTION...")
                formatted_content = self._format_bullet_content(insight.key_insight, insight)
                print(f"      🔧 FORMATTING FUNCTION COMPLETED")
                
                # Ensure content is properly formatted
                final_content = self._format_bullet_content(formatted_content, insight)
                
                operations.append(DeltaOperation(
                    operation="ADD",
                    content=final_content,
                    section=section,
                    helpful_increment=1,
                    harmful_increment=0
                ))
        else:
            print(f"      ⚠️ Low confidence insight ({insight.confidence}), skipping...")
        
        # Create delta update
        delta = DeltaUpdate(
            operations=operations,
            timestamp=datetime.now().isoformat(),
            source_feedback_id=feedback_id,
            total_operations=len(operations)
        )
        
        print(f"      📋 Created delta with {len(operations)} operations")
        return delta
    
    def merge_delta(self, delta: DeltaUpdate) -> bool:
        """Apply delta operations to playbook (deterministic, no LLM)"""
        
        print(f"   💾 Applying delta operations to playbook...")
        
        try:
            for i, operation in enumerate(delta.operations):
                print(f"      🔧 Operation {i+1}: {operation.operation}")
                
                if operation.operation == "ADD":
                    # Add new bullet
                    bullet_id = playbook_manager.add_bullet(
                        content=operation.content,
                        section=operation.section or "General"
                    )
                    print(f"         ✅ Added new bullet: {bullet_id}")
                    print(f"         📝 Content: {operation.content[:100]}...")
                    
                elif operation.operation == "UPDATE":
                    # Update existing bullet counters
                    if operation.bullet_id:
                        for _ in range(operation.helpful_increment):
                            playbook_manager.update_counters(operation.bullet_id, helpful=True)
                        for _ in range(operation.harmful_increment):
                            playbook_manager.update_counters(operation.bullet_id, helpful=False)
                        print(f"         ✅ Updated bullet: {operation.bullet_id}")
                        print(f"         📊 Helpful: +{operation.helpful_increment}, Harmful: +{operation.harmful_increment}")
            
            # Save delta log
            self._save_delta_log(delta)
            print(f"      📄 Delta log saved")
            
            return True
            
        except Exception as e:
            print(f"      ❌ Error merging delta: {e}")
            return False
    
    def _find_similar_bullets(self, content: str, threshold: float = 0.8) -> List[Bullet]:
        """Find bullets similar to the given content"""
        if not playbook_manager.bullets:
            return []
        
        # Use FAISS to find similar bullets
        relevant_bullets = playbook_manager.retrieve_relevant(content, top_k=5)
        
        # Filter by similarity threshold (this is approximate since we're using FAISS)
        # In a more sophisticated implementation, we'd calculate exact cosine similarity
        return relevant_bullets[:3]  # Return top 3 as potential matches
    
    def _format_bullet_content(self, content: str, insight: ReflectionInsight) -> str:
        """Format bullet content to ensure ACE compliance using LangChain best practices"""
        
        print(f"      🔧 FORMATTING DEBUG:")
        print(f"         Original content: {content[:100]}...")
        print(f"         Contains tech terms: {any(tech_term in content for tech_term in ['HumanMessage', 'AIMessage', '{', '}', 'additional_kwargs', 'response_metadata'])}")
        
        # LangChain-based content cleaning and formatting
        formatted = self._clean_and_format_content(content, insight)
        
        print(f"         Final formatted: {formatted[:100]}...")
        return formatted
    
    def _clean_and_format_content(self, content: str, insight: ReflectionInsight) -> str:
        """Clean and format content using LangChain-style processing"""
        
        # Step 1: Detect and remove raw object data (LangChain output cleaning)
        if any(tech_term in content for tech_term in ["HumanMessage", "AIMessage", "{", "}", "additional_kwargs", "response_metadata"]):
            print(f"         🔄 Cleaning raw object data with LangChain-style processing")
            # Use insight data to create clean, actionable content
            if insight.error_identification and "no error" not in insight.error_identification.lower():
                # Error case - create actionable "avoid" guidance
                formatted = f"When {insight.error_identification.lower()}, avoid this approach and instead: {insight.correct_approach}"
            else:
                # Success case - create actionable "use this" guidance
                formatted = f"When answering similar questions, use this approach: {insight.correct_approach}"
        else:
            # Content is already clean, use it as-is
            formatted = content.strip()
        
        # Step 2: Apply LangChain-style structured formatting
        formatted = self._apply_structured_formatting(formatted)
        
        # Step 3: Ensure actionable content (LangChain output validation)
        if not formatted or len(formatted) < 10:
            formatted = self._create_fallback_insight(insight)
        
        return formatted
    
    def _apply_structured_formatting(self, content: str) -> str:
        """Apply LangChain-style structured formatting"""
        
        # Convert to numbered list if multiple points (LangChain list formatting)
        if '\n' in content and not content.startswith(('1.', '2.', '3.', '4.', '5.')):
            lines = content.split('\n')
            if len(lines) > 1:
                numbered_lines = []
                for i, line in enumerate(lines, 1):
                    if line.strip():
                        numbered_lines.append(f"{i}. {line.strip()}")
                content = '\n'.join(numbered_lines)
        
        return content.strip()
    
    def _create_fallback_insight(self, insight: ReflectionInsight) -> str:
        """Create fallback insight using LangChain-style content generation"""
        
        if insight.error_identification and "no error" not in insight.error_identification.lower():
            return f"When {insight.error_identification.lower()}, use this approach: {insight.correct_approach}"
        else:
            return f"Success pattern: {insight.correct_approach}"
    
    def _determine_section(self, insight: ReflectionInsight) -> str:
        """Determine appropriate section for the insight"""
        
        # Analyze the insight content to determine section
        content_lower = insight.key_insight.lower()
        
        if any(word in content_lower for word in ["explain", "definition", "what is", "describe"]):
            return "Explanation Strategies"
        elif any(word in content_lower for word in ["calculate", "math", "compute", "solve"]):
            return "Calculation Strategies"
        elif any(word in content_lower for word in ["search", "find", "look up", "research"]):
            return "Search Strategies"
        elif any(word in content_lower for word in ["time", "date", "schedule"]):
            return "Time Management"
        elif any(word in content_lower for word in ["user", "personal", "individual"]):
            return "User Interaction"
        elif any(word in content_lower for word in ["error", "mistake", "wrong", "incorrect"]):
            return "Error Prevention"
        elif any(word in content_lower for word in ["format", "structure", "organize", "bullet"]):
            return "Response Formatting"
        else:
            return "General Strategies"
    
    def _save_delta_log(self, delta: DeltaUpdate):
        """Save delta update log for tracking"""
        
        log_data = {
            "timestamp": delta.timestamp,
            "source_feedback_id": delta.source_feedback_id,
            "total_operations": delta.total_operations,
            "operations": [
                {
                    "operation": op.operation,
                    "bullet_id": op.bullet_id,
                    "content": op.content,
                    "section": op.section,
                    "helpful_increment": op.helpful_increment,
                    "harmful_increment": op.harmful_increment
                }
                for op in delta.operations
            ]
        }
        
        filename = f"update_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(self.updates_dir, filename)
        
        try:
            with open(filepath, 'w') as f:
                json.dump(log_data, f, indent=2)
        except Exception as e:
            print(f"Error saving delta log: {e}")
    
    def deduplicate_playbook(self, similarity_threshold: float = 0.9) -> int:
        """Remove duplicate bullets from playbook"""
        return playbook_manager.deduplicate(similarity_threshold)
    
    def get_playbook_stats(self) -> Dict[str, Any]:
        """Get current playbook statistics"""
        return playbook_manager.get_stats()
    
    def create_insight_bullet(self, insight: ReflectionInsight, section: str = "General") -> str:
        """Create a new bullet directly from insight"""
        
        # Format the insight as a bullet
        bullet_content = f"{insight.key_insight}"
        
        # Add context if available
        if insight.error_identification:
            bullet_content += f"\n\nContext: {insight.error_identification}"
        
        if insight.correct_approach:
            bullet_content += f"\n\nCorrect approach: {insight.correct_approach}"
        
        # Add bullet to playbook
        bullet_id = playbook_manager.add_bullet(
            content=bullet_content,
            section=section
        )
        
        return bullet_id
    
    def process_negative_feedback(self, insight: ReflectionInsight, feedback_id: str) -> DeltaUpdate:
        """Process negative feedback to identify harmful patterns"""
        
        operations = []
        
        # For negative feedback, we might want to:
        # 1. Add a bullet about what NOT to do
        # 2. Update existing bullets that were harmful
        
        if insight.confidence > 0.6:  # Only process high-confidence negative feedback
            
            # Create a "what not to do" bullet
            dont_do_content = f"AVOID: {insight.error_identification}\n\nInstead: {insight.correct_approach}"
            
            operations.append(DeltaOperation(
                operation="ADD",
                content=dont_do_content,
                section="Anti-Patterns",
                helpful_increment=1,
                harmful_increment=0
            ))
        
        # Create delta update
        delta = DeltaUpdate(
            operations=operations,
            timestamp=datetime.now().isoformat(),
            source_feedback_id=feedback_id,
            total_operations=len(operations)
        )
        
        return delta
    
    def process_positive_feedback(self, insight: ReflectionInsight, feedback_id: str) -> DeltaUpdate:
        """Process positive feedback to reinforce good patterns"""
        
        operations = []
        
        if insight.confidence > 0.5:  # Process positive feedback
            
            # Create a "success pattern" bullet
            success_content = f"SUCCESS PATTERN: {insight.key_insight}"
            
            operations.append(DeltaOperation(
                operation="ADD",
                content=success_content,
                section="Success Patterns",
                helpful_increment=1,
                harmful_increment=0
            ))
        
        # Create delta update
        delta = DeltaUpdate(
            operations=operations,
            timestamp=datetime.now().isoformat(),
            source_feedback_id=feedback_id,
            total_operations=len(operations)
        )
        
        return delta


# Global curator instance
curator_agent = CuratorAgent()
