"""
Chat Data Storage System
Stores chat interactions for feedback linking.
"""

import json
import time
from typing import Dict, Optional
from pathlib import Path


class ChatStorage:
    """Stores chat data for feedback linking."""
    
    def __init__(self, storage_dir: str = "chat_storage"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        
        # In-memory cache for quick access
        self._chat_cache = {}
    
    def store_chat_data(self, feedback_id: str, user_id: str, user_name: str, 
                       question: str, model_response: str, tools_used: str = None, 
                       confidence: str = "medium", used_bullets: list = None) -> bool:
        """Store chat data for a feedback ID."""
        try:
            chat_data = {
                "feedback_id": feedback_id,
                "user_id": user_id,
                "user_name": user_name,
                "question": question,
                "model_response": model_response,
                "tools_used": tools_used,
                "confidence": confidence,
                "used_bullets": used_bullets or [],  # Track which bullets were used
                "timestamp": time.time(),
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Store in memory cache
            self._chat_cache[feedback_id] = chat_data
            
            # Store in file for persistence
            file_path = self.storage_dir / f"chat_{feedback_id}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(chat_data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"Error storing chat data: {e}")
            return False
    
    def get_chat_data(self, feedback_id: str) -> Optional[Dict]:
        """Retrieve chat data by feedback ID."""
        # First try memory cache
        if feedback_id in self._chat_cache:
            return self._chat_cache[feedback_id]
        
        # Then try file storage
        try:
            file_path = self.storage_dir / f"chat_{feedback_id}.json"
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    chat_data = json.load(f)
                    # Store in cache for future access
                    self._chat_cache[feedback_id] = chat_data
                    return chat_data
        except Exception as e:
            print(f"Error retrieving chat data: {e}")
        
        return None
    
    def update_chat_response(self, feedback_id: str, model_response: str) -> bool:
        """Update the model response for existing chat data."""
        try:
            # Update memory cache
            if feedback_id in self._chat_cache:
                self._chat_cache[feedback_id]["model_response"] = model_response
                
                # Update file storage
                file_path = self.storage_dir / f"chat_{feedback_id}.json"
                if file_path.exists():
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(self._chat_cache[feedback_id], f, indent=2, ensure_ascii=False)
                    return True
            return False
        except Exception as e:
            print(f"Error updating chat response: {e}")
            return False
    
    def get_user_chats(self, user_id: str) -> list:
        """Get all chat data for a specific user."""
        user_chats = []
        
        # Check memory cache
        for feedback_id, chat_data in self._chat_cache.items():
            if chat_data.get('user_id') == user_id:
                user_chats.append(chat_data)
        
        # Check file storage
        for file_path in self.storage_dir.glob("chat_*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    chat_data = json.load(f)
                    if chat_data.get('user_id') == user_id:
                        user_chats.append(chat_data)
            except Exception as e:
                print(f"Error reading chat file {file_path}: {e}")
        
        return sorted(user_chats, key=lambda x: x.get('timestamp', 0), reverse=True)
    
    def clear_old_chats(self, days: int = 30):
        """Clear chat data older than specified days."""
        import time
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        
        for file_path in self.storage_dir.glob("chat_*.json"):
            if file_path.stat().st_mtime < cutoff_time:
                file_path.unlink()
                print(f"Cleared old chat file: {file_path}")


# Global chat storage instance
chat_storage = ChatStorage()
