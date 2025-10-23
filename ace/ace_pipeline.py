"""
ACE Processing Pipeline
Handles the complete ACE cycle: Feedback -> Reflector -> Curator -> Playbook Update
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from playbook_manager import playbook_manager
from reflector_agent import reflector_agent, ReflectionInsight
from curator_agent import curator_agent, DeltaUpdate
from chat_storage import chat_storage
from feedback_system import FeedbackManager
from logging_config import log_error, log_chat_interaction


@dataclass
class ACEProcessingResult:
    """Result of ACE processing cycle"""
    success: bool
    feedback_id: str
    insights_generated: int
    bullets_added: int
    bullets_updated: int
    processing_time: float
    error_message: Optional[str] = None


class ACEPipeline:
    """Main pipeline for processing feedback through ACE cycle"""
    
    def __init__(self):
        self.feedback_manager = FeedbackManager()
        self.processing_log = []
        self.pending_feedback = []
    
    async def process_feedback(self, feedback_id: str) -> ACEProcessingResult:
        """Process a single feedback through the complete ACE cycle"""
        
        start_time = datetime.now()
        print(f"\n🔄 ACE Processing Started for feedback_id: {feedback_id}")
        
        try:
            # 1. Get feedback data
            print(f"📥 Step 1: Retrieving feedback data for {feedback_id}")
            feedback_data = self.feedback_manager.get_feedback(feedback_id)
            if not feedback_data:
                print(f"❌ Feedback not found: {feedback_id}")
                return ACEProcessingResult(
                    success=False,
                    feedback_id=feedback_id,
                    insights_generated=0,
                    bullets_added=0,
                    bullets_updated=0,
                    processing_time=0.0,
                    error_message="Feedback not found"
                )
            
            print(f"✅ Feedback retrieved: {feedback_data.feedback_type} (rating: {feedback_data.rating})")
            
            # 2. Get chat data
            print(f"📥 Step 2: Retrieving chat data for {feedback_id}")
            chat_data = chat_storage.get_chat_data(feedback_id)
            if not chat_data:
                print(f"❌ Chat data not found: {feedback_id}")
                return ACEProcessingResult(
                    success=False,
                    feedback_id=feedback_id,
                    insights_generated=0,
                    bullets_added=0,
                    bullets_updated=0,
                    processing_time=0.0,
                    error_message="Chat data not found"
                )
            
            print(f"✅ Chat data retrieved: Question: {chat_data.get('question', '')[:50]}...")
            
            # 3. Run Reflector
            print(f"🧠 Step 3: Running Reflector agent...")
            insight = await self._run_reflector(chat_data, feedback_data)
            
            if insight:
                print(f"✅ Reflector generated insight: {insight.key_insight[:100]}...")
                print(f"   - Error identification: {insight.error_identification[:100]}...")
                print(f"   - Confidence: {insight.confidence}")
            else:
                print(f"⚠️ Reflector failed to generate insight")
            
            # 4. Run Curator
            print(f"📚 Step 4: Running Curator agent...")
            delta = await self._run_curator(insight, feedback_id)
            
            print(f"✅ Curator created delta with {delta.total_operations} operations")
            for i, op in enumerate(delta.operations):
                print(f"   - Operation {i+1}: {op.operation} - {op.content[:50] if op.content else 'Update existing'}...")
            
            # 5. Apply updates
            print(f"💾 Step 5: Applying updates to playbook...")
            success = await self._apply_updates(delta)
            
            # 6. Update bullet counters based on feedback
            print(f"📊 Step 6: Updating bullet counters...")
            await self._update_bullet_counters(chat_data, feedback_data)
            
            if success:
                print(f"✅ Playbook updated successfully")
            else:
                print(f"❌ Failed to update playbook")
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Create result
            result = ACEProcessingResult(
                success=success,
                feedback_id=feedback_id,
                insights_generated=1 if insight else 0,
                bullets_added=len([op for op in delta.operations if op.operation == "ADD"]),
                bullets_updated=len([op for op in delta.operations if op.operation == "UPDATE"]),
                processing_time=processing_time
            )
            
            # Log processing
            self._log_processing(result)
            
            # Print final summary
            print(f"\n🎯 ACE Processing Complete for {feedback_id}:")
            print(f"   ✅ Success: {result.success}")
            print(f"   📊 Insights generated: {result.insights_generated}")
            print(f"   ➕ Bullets added: {result.bullets_added}")
            print(f"   🔄 Bullets updated: {result.bullets_updated}")
            print(f"   ⏱️ Processing time: {result.processing_time:.3f}s")
            if result.error_message:
                print(f"   ❌ Error: {result.error_message}")
            
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            return ACEProcessingResult(
                success=False,
                feedback_id=feedback_id,
                insights_generated=0,
                bullets_added=0,
                bullets_updated=0,
                processing_time=processing_time,
                error_message=str(e)
            )
    
    async def _run_reflector(self, chat_data: Dict[str, Any], feedback_data) -> Optional[ReflectionInsight]:
        """Run Reflector agent to analyze feedback"""
        
        try:
            # Determine feedback type for processing
            feedback_type = feedback_data.feedback_type
            rating = feedback_data.rating
            
            if feedback_type == "incorrect" or rating <= 2:
                # Negative feedback - analyze what went wrong
                insight = reflector_agent.analyze_feedback(chat_data, feedback_data)
            elif feedback_type == "correct" or rating >= 4:
                # Positive feedback - extract success patterns
                insight = reflector_agent.extract_insights_from_success(
                    chat_data.get("question", ""),
                    chat_data.get("model_response", ""),
                    feedback_type,
                    rating
                )
            else:
                # Neutral/partial feedback - still analyze
                insight = reflector_agent.analyze_feedback(chat_data, feedback_data)
            
            return insight
            
        except Exception as e:
            print(f"Error in Reflector: {e}")
            return None
    
    async def _run_curator(self, insight: Optional[ReflectionInsight], feedback_id: str) -> DeltaUpdate:
        """Run Curator agent to create playbook updates"""
        
        if not insight:
            # No insight available, create empty delta
            return DeltaUpdate(
                operations=[],
                timestamp=datetime.now().isoformat(),
                source_feedback_id=feedback_id,
                total_operations=0
            )
        
        try:
            # Process insight based on type
            feedback_type = insight.error_identification.lower()
            
            if "success" in feedback_type or "correct" in feedback_type:
                delta = curator_agent.process_positive_feedback(insight, feedback_id)
            elif "error" in feedback_type or "wrong" in feedback_type:
                delta = curator_agent.process_negative_feedback(insight, feedback_id)
            else:
                delta = curator_agent.process_insights(insight, feedback_id)
            
            return delta
            
        except Exception as e:
            print(f"Error in Curator: {e}")
            return DeltaUpdate(
                operations=[],
                timestamp=datetime.now().isoformat(),
                source_feedback_id=feedback_id,
                total_operations=0
            )
    
    async def _apply_updates(self, delta: DeltaUpdate) -> bool:
        """Apply delta updates to playbook"""
        
        try:
            success = curator_agent.merge_delta(delta)
            return success
        except Exception as e:
            print(f"Error applying updates: {e}")
            return False
    
    def _log_processing(self, result: ACEProcessingResult):
        """Log processing result"""
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "feedback_id": result.feedback_id,
            "success": result.success,
            "insights_generated": result.insights_generated,
            "bullets_added": result.bullets_added,
            "bullets_updated": result.bullets_updated,
            "processing_time": result.processing_time,
            "error_message": result.error_message
        }
        
        self.processing_log.append(log_entry)
        
        # Save to file
        log_file = "ace/ace_processing_log.json"
        try:
            with open(log_file, 'w') as f:
                json.dump(self.processing_log, f, indent=2)
        except Exception as e:
            print(f"Error saving processing log: {e}")
    
    async def process_pending_feedback(self) -> List[ACEProcessingResult]:
        """Process all pending feedback"""
        
        results = []
        
        # Get all feedback that hasn't been processed
        all_feedback = self.feedback_manager.get_all_feedback()
        
        for feedback in all_feedback:
            feedback_id = feedback.feedback_id
            if feedback_id and feedback_id not in [r.feedback_id for r in results]:
                result = await self.process_feedback(feedback_id)
                results.append(result)
        
        return results
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        
        if not self.processing_log:
            return {
                "total_processed": 0,
                "success_rate": 0.0,
                "avg_processing_time": 0.0,
                "total_bullets_added": 0,
                "total_bullets_updated": 0
            }
        
        total_processed = len(self.processing_log)
        successful = len([r for r in self.processing_log if r.get("success", False)])
        success_rate = successful / total_processed if total_processed > 0 else 0.0
        
        avg_processing_time = sum(r.get("processing_time", 0) for r in self.processing_log) / total_processed
        
        total_bullets_added = sum(r.get("bullets_added", 0) for r in self.processing_log)
        total_bullets_updated = sum(r.get("bullets_updated", 0) for r in self.processing_log)
        
        return {
            "total_processed": total_processed,
            "success_rate": success_rate,
            "avg_processing_time": avg_processing_time,
            "total_bullets_added": total_bullets_added,
            "total_bullets_updated": total_bullets_updated,
            "playbook_stats": playbook_manager.get_stats()
        }
    
    async def trigger_ace_update(self, feedback_id: str) -> Dict[str, Any]:
        """Manually trigger ACE update for specific feedback"""
        
        result = await self.process_feedback(feedback_id)
        
        return {
            "success": result.success,
            "feedback_id": result.feedback_id,
            "insights_generated": result.insights_generated,
            "bullets_added": result.bullets_added,
            "bullets_updated": result.bullets_updated,
            "processing_time": result.processing_time,
            "error_message": result.error_message
        }
    
    async def _update_bullet_counters(self, chat_data, feedback_data):
        """Update bullet counters based on feedback"""
        try:
            used_bullets = chat_data.get("used_bullets", [])
            if not used_bullets:
                print(f"      ⚠️ No bullets were used in this interaction")
                return
            
            print(f"      📌 Updating counters for {len(used_bullets)} used bullets")
            
            # Determine if feedback is positive or negative
            is_positive = feedback_data.rating >= 4 or feedback_data.feedback_type == "positive"
            is_negative = feedback_data.rating <= 2 or feedback_data.feedback_type == "incorrect"
            
            for bullet_id in used_bullets:
                if is_positive:
                    print(f"         ✅ Bullet {bullet_id}: +1 helpful (positive feedback)")
                    playbook_manager.update_counters(bullet_id, helpful=True)
                elif is_negative:
                    print(f"         ❌ Bullet {bullet_id}: +1 harmful (negative feedback)")
                    playbook_manager.update_counters(bullet_id, helpful=False)
                else:
                    print(f"         ➖ Bullet {bullet_id}: neutral feedback")
            
            # Save updated playbook
            playbook_manager.save_playbook()
            print(f"      ✅ Bullet counters updated and saved")
            
        except Exception as e:
            print(f"      ❌ Error updating bullet counters: {e}")


# Global ACE pipeline instance
ace_pipeline = ACEPipeline()
