"""
ACE Background Worker
Processes feedback in batches and maintains playbook
"""

import asyncio
import time
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
from ace_pipeline import ace_pipeline, ACEProcessingResult
from playbook_manager import playbook_manager
from feedback_system import FeedbackManager


class ACEWorker:
    """Background worker for processing feedback through ACE pipeline"""
    
    def __init__(self, batch_size: int = 5, processing_interval: int = 300):
        self.batch_size = batch_size
        self.processing_interval = processing_interval  # seconds
        self.feedback_manager = FeedbackManager()
        self.is_running = False
        self.processed_feedback = set()
        self.worker_log = []
        
        # Create worker log directory
        os.makedirs("ace/worker_logs", exist_ok=True)
    
    async def start_worker(self):
        """Start the background worker"""
        self.is_running = True
        print(f"ACE Worker started - processing every {self.processing_interval} seconds")
        
        while self.is_running:
            try:
                await self._process_batch()
                await asyncio.sleep(self.processing_interval)
            except Exception as e:
                print(f"Error in ACE Worker: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    def stop_worker(self):
        """Stop the background worker"""
        self.is_running = False
        print("ACE Worker stopped")
    
    async def _process_batch(self):
        """Process a batch of pending feedback"""
        
        # Get unprocessed feedback
        pending_feedback = self._get_pending_feedback()
        
        if not pending_feedback:
            print("No pending feedback to process")
            return
        
        print(f"Processing {len(pending_feedback)} feedback items")
        
        # Process in batches
        for i in range(0, len(pending_feedback), self.batch_size):
            batch = pending_feedback[i:i + self.batch_size]
            await self._process_feedback_batch(batch)
            
            # Small delay between batches
            await asyncio.sleep(1)
    
    def _get_pending_feedback(self) -> List[Dict[str, Any]]:
        """Get feedback that hasn't been processed yet"""
        
        try:
            # Get all feedback
            all_feedback = self.feedback_manager.get_all_feedback()
            
            # Filter out already processed
            pending = []
            for feedback in all_feedback:
                feedback_id = feedback.get("feedback_id")
                if feedback_id and feedback_id not in self.processed_feedback:
                    pending.append(feedback)
            
            return pending
            
        except Exception as e:
            print(f"Error getting pending feedback: {e}")
            return []
    
    async def _process_feedback_batch(self, feedback_batch: List[Dict[str, Any]]):
        """Process a batch of feedback"""
        
        batch_results = []
        
        for feedback in feedback_batch:
            feedback_id = feedback.get("feedback_id")
            if not feedback_id:
                continue
            
            try:
                # Process through ACE pipeline
                result = await ace_pipeline.process_feedback(feedback_id)
                batch_results.append(result)
                
                # Mark as processed
                self.processed_feedback.add(feedback_id)
                
                # Log result
                self._log_processing_result(result)
                
            except Exception as e:
                print(f"Error processing feedback {feedback_id}: {e}")
                
                # Create error result
                error_result = ACEProcessingResult(
                    success=False,
                    feedback_id=feedback_id,
                    insights_generated=0,
                    bullets_added=0,
                    bullets_updated=0,
                    processing_time=0.0,
                    error_message=str(e)
                )
                batch_results.append(error_result)
        
        # Log batch results
        self._log_batch_results(batch_results)
        
        # Print summary
        successful = len([r for r in batch_results if r.success])
        total_bullets_added = sum(r.bullets_added for r in batch_results)
        total_bullets_updated = sum(r.bullets_updated for r in batch_results)
        
        print(f"Batch processed: {successful}/{len(batch_results)} successful")
        print(f"Bullets added: {total_bullets_added}, updated: {total_bullets_updated}")
    
    def _log_processing_result(self, result: ACEProcessingResult):
        """Log individual processing result"""
        
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
        
        self.worker_log.append(log_entry)
    
    def _log_batch_results(self, results: List[ACEProcessingResult]):
        """Log batch processing results"""
        
        batch_log = {
            "timestamp": datetime.now().isoformat(),
            "batch_size": len(results),
            "successful": len([r for r in results if r.success]),
            "failed": len([r for r in results if not r.success]),
            "total_bullets_added": sum(r.bullets_added for r in results),
            "total_bullets_updated": sum(r.bullets_updated for r in results),
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
            ]
        }
        
        # Save batch log
        log_file = f"ace/worker_logs/batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(log_file, 'w') as f:
                json.dump(batch_log, f, indent=2)
        except Exception as e:
            print(f"Error saving batch log: {e}")
    
    def get_worker_stats(self) -> Dict[str, Any]:
        """Get worker statistics"""
        
        if not self.worker_log:
            return {
                "total_processed": 0,
                "success_rate": 0.0,
                "avg_processing_time": 0.0,
                "total_bullets_added": 0,
                "total_bullets_updated": 0,
                "is_running": self.is_running
            }
        
        total_processed = len(self.worker_log)
        successful = len([r for r in self.worker_log if r.get("success", False)])
        success_rate = successful / total_processed if total_processed > 0 else 0.0
        
        avg_processing_time = sum(r.get("processing_time", 0) for r in self.worker_log) / total_processed
        
        total_bullets_added = sum(r.get("bullets_added", 0) for r in self.worker_log)
        total_bullets_updated = sum(r.get("bullets_updated", 0) for r in self.worker_log)
        
        return {
            "total_processed": total_processed,
            "success_rate": success_rate,
            "avg_processing_time": avg_processing_time,
            "total_bullets_added": total_bullets_added,
            "total_bullets_updated": total_bullets_updated,
            "is_running": self.is_running,
            "processed_feedback_count": len(self.processed_feedback)
        }
    
    async def process_all_immediately(self) -> Dict[str, Any]:
        """Process all pending feedback immediately"""
        
        print("Processing all pending feedback immediately...")
        
        # Get all pending feedback
        pending_feedback = self._get_pending_feedback()
        
        if not pending_feedback:
            return {
                "success": True,
                "message": "No pending feedback to process",
                "total_processed": 0
            }
        
        # Process all feedback
        results = []
        for feedback in pending_feedback:
            feedback_id = feedback.get("feedback_id")
            if feedback_id:
                try:
                    result = await ace_pipeline.process_feedback(feedback_id)
                    results.append(result)
                    self.processed_feedback.add(feedback_id)
                except Exception as e:
                    print(f"Error processing {feedback_id}: {e}")
        
        # Calculate summary
        total_processed = len(results)
        successful = len([r for r in results if r.success])
        total_bullets_added = sum(r.bullets_added for r in results)
        total_bullets_updated = sum(r.bullets_updated for r in results)
        
        return {
            "success": True,
            "message": f"Processed {total_processed} feedback items",
            "total_processed": total_processed,
            "successful": successful,
            "failed": total_processed - successful,
            "total_bullets_added": total_bullets_added,
            "total_bullets_updated": total_bullets_updated
        }
    
    async def cleanup_old_logs(self, days_to_keep: int = 7):
        """Clean up old worker logs"""
        
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        logs_dir = "ace/worker_logs"
        
        if not os.path.exists(logs_dir):
            return
        
        try:
            for filename in os.listdir(logs_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(logs_dir, filename)
                    file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                    
                    if file_time < cutoff_date:
                        os.remove(filepath)
                        print(f"Removed old log: {filename}")
        
        except Exception as e:
            print(f"Error cleaning up logs: {e}")


# Global worker instance
ace_worker = ACEWorker()


async def start_ace_worker():
    """Start the ACE background worker"""
    await ace_worker.start_worker()


def stop_ace_worker():
    """Stop the ACE background worker"""
    ace_worker.stop_worker()


if __name__ == "__main__":
    # Run worker standalone
    print("Starting ACE Worker...")
    asyncio.run(start_ace_worker())
