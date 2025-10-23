"""
Playbook Manager for ACE Framework
Manages structured playbook with FAISS-based semantic retrieval
"""

import os
import json
import uuid
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import faiss
import numpy as np
from langchain.embeddings import init_embeddings
from dataclasses import dataclass, asdict
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Bullet:
    """Represents a single playbook bullet with metadata"""
    id: str 
    helpful: int = 0
    harmful: int = 0
    content: str = ""
    section: str = "General"
    created_at: str = ""
    last_used: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.last_used:
            self.last_used = self.created_at
    
    def to_markdown(self) -> str:
        """Convert bullet to markdown format"""
        return f"[{self.id}] helpful={self.helpful} harmful={self.harmful} ::\n{self.content}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


class PlaybookManager:
    """Manages playbook with FAISS-based semantic retrieval"""
    
    def __init__(self, playbook_dir: str = "ace/playbook"):
        self.playbook_dir = playbook_dir
        self.embedding_model = init_embeddings("openai:text-embedding-3-small")
        self.embedding_dim = 1536  # text-embedding-3-small dimension
        
        print(f"🏗️ Initializing PlaybookManager...")
        print(f"   📁 Playbook directory: {playbook_dir}")
        print(f"   🔤 Embedding model: text-embedding-3-small ({self.embedding_dim} dimensions)")
        
        # Initialize FAISS index
        self.index = faiss.IndexFlatIP(self.embedding_dim)  # Inner product for cosine similarity
        self.bullets: List[Bullet] = []
        self.bullet_id_to_index: Dict[str, int] = {}
        
        # File paths
        self.playbook_file = os.path.join(playbook_dir, "playbook.md")
        self.metadata_file = os.path.join(playbook_dir, "metadata.json")
        self.embeddings_file = os.path.join(playbook_dir, "embeddings.faiss")
        
        print(f"   📄 Files to be created:")
        print(f"      - Playbook: {self.playbook_file}")
        print(f"      - Metadata: {self.metadata_file}")
        print(f"      - FAISS Index: {self.embeddings_file}")
        
        # Create directory if it doesn't exist
        os.makedirs(playbook_dir, exist_ok=True)
        print(f"   📁 Directory created: {playbook_dir}")
        
        # Load existing playbook
        print(f"   📥 Loading existing playbook...")
        self.load_playbook()
    
    def _get_embedding(self, text: str) -> np.ndarray:
        """Get OpenAI embedding for text using LangChain"""
        try:
            embedding = self.embedding_model.embed_query(text)
            return np.array(embedding, dtype=np.float32)
        except Exception as e:
            print(f"Error getting embedding: {e}")
            # Return zero vector as fallback
            return np.zeros(self.embedding_dim, dtype=np.float32)
    
    def _normalize_embedding(self, embedding: np.ndarray) -> np.ndarray:
        """Normalize embedding for cosine similarity"""
        norm = np.linalg.norm(embedding)
        if norm > 0:
            return embedding / norm
        return embedding
    
    def add_bullet(self, content: str, section: str = "General") -> str:
        """Add new bullet to playbook"""
        bullet_id = f"ctx-{str(uuid.uuid4())[:8]}"
        bullet = Bullet(
            id=bullet_id,
            content=content,
            section=section,
            created_at=datetime.now().isoformat()
        )
        
        print(f"         📝 Creating bullet {bullet_id} in section '{section}'")
        print(f"         📄 Content: {content[:100]}...")
        
        # Add to list
        self.bullets.append(bullet)
        self.bullet_id_to_index[bullet_id] = len(self.bullets) - 1
        
        # Get embedding and add to FAISS index
        embedding = self._get_embedding(content)
        normalized_embedding = self._normalize_embedding(embedding)
        self.index.add(normalized_embedding.reshape(1, -1))
        
        # Save updated playbook
        self.save_playbook()
        print(f"         💾 Playbook saved with {len(self.bullets)} bullets")
        
        return bullet_id
    
    def update_counters(self, bullet_id: str, helpful: bool = True) -> bool:
        """Update helpful/harmful counters for a bullet"""
        if bullet_id not in self.bullet_id_to_index:
            return False
        
        index = self.bullet_id_to_index[bullet_id]
        bullet = self.bullets[index]
        
        if helpful:
            bullet.helpful += 1
        else:
            bullet.harmful += 1
        
        bullet.last_used = datetime.now().isoformat()
        
        # Save updated playbook
        self.save_playbook()
        
        return True
    
    def retrieve_relevant(self, query: str, top_k: int = 10) -> List[Bullet]:
        """Retrieve most relevant bullets for a query"""
        if not self.bullets:
            print(f"   📚 Playbook is empty, no bullets to retrieve")
            return []
        
        print(f"   🔍 Searching playbook for: '{query[:50]}...'")
        print(f"   📊 Total bullets in playbook: {len(self.bullets)}")
        
        # Get query embedding
        query_embedding = self._get_embedding(query)
        normalized_query = self._normalize_embedding(query_embedding)
        
        # Search FAISS index
        scores, indices = self.index.search(normalized_query.reshape(1, -1), min(top_k, len(self.bullets)))
        
        # Return relevant bullets
        relevant_bullets = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.bullets):
                bullet = self.bullets[idx]
                # Only return bullets that are more helpful than harmful
                if bullet.helpful >= bullet.harmful:
                    relevant_bullets.append(bullet)
        
        print(f"   ✅ Found {len(relevant_bullets)} relevant bullets")
        for i, bullet in enumerate(relevant_bullets[:3]):  # Show first 3
            print(f"      {i+1}. [{bullet.id}] {bullet.content[:60]}... (helpful: {bullet.helpful}, harmful: {bullet.harmful})")
        
        return relevant_bullets[:top_k]
    
    def deduplicate(self, similarity_threshold: float = 0.9) -> int:
        """Remove duplicate bullets based on semantic similarity"""
        if len(self.bullets) < 2:
            return 0
        
        duplicates_removed = 0
        bullets_to_remove = set()
        
        # Compare all pairs
        for i in range(len(self.bullets)):
            if i in bullets_to_remove:
                continue
                
            for j in range(i + 1, len(self.bullets)):
                if j in bullets_to_remove:
                    continue
                
                # Calculate cosine similarity
                bullet_i = self.bullets[i]
                bullet_j = self.bullets[j]
                
                # Get embeddings
                emb_i = self._get_embedding(bullet_i.content)
                emb_j = self._get_embedding(bullet_j.content)
                
                # Calculate cosine similarity
                norm_i = np.linalg.norm(emb_i)
                norm_j = np.linalg.norm(emb_j)
                
                if norm_i > 0 and norm_j > 0:
                    similarity = np.dot(emb_i, emb_j) / (norm_i * norm_j)
                    
                    if similarity >= similarity_threshold:
                        # Merge bullets (keep the one with better ratio)
                        ratio_i = bullet_i.helpful / max(bullet_i.harmful, 1)
                        ratio_j = bullet_j.helpful / max(bullet_j.harmful, 1)
                        
                        if ratio_i >= ratio_j:
                            # Merge j into i
                            bullet_i.helpful += bullet_j.helpful
                            bullet_i.harmful += bullet_j.harmful
                            bullets_to_remove.add(j)
                        else:
                            # Merge i into j
                            bullet_j.helpful += bullet_i.helpful
                            bullet_j.harmful += bullet_i.harmful
                            bullets_to_remove.add(i)
                            break
        
        # Remove duplicates
        if bullets_to_remove:
            self.bullets = [bullet for i, bullet in enumerate(self.bullets) if i not in bullets_to_remove]
            duplicates_removed = len(bullets_to_remove)
            
            # Rebuild FAISS index
            self._rebuild_index()
            
            # Save updated playbook
            self.save_playbook()
        
        return duplicates_removed
    
    def _rebuild_index(self):
        """Rebuild FAISS index from current bullets"""
        print(f"      🔧 Rebuilding FAISS index...")
        self.index = faiss.IndexFlatIP(self.embedding_dim)
        self.bullet_id_to_index = {}
        
        for i, bullet in enumerate(self.bullets):
            self.bullet_id_to_index[bullet.id] = i
            print(f"         📝 Processing bullet {i+1}/{len(self.bullets)}: {bullet.id}")
            embedding = self._get_embedding(bullet.content)
            normalized_embedding = self._normalize_embedding(embedding)
            self.index.add(normalized_embedding.reshape(1, -1))
        
        print(f"      ✅ FAISS index rebuilt with {len(self.bullets)} bullets")
    
    def get_bullet(self, bullet_id: str) -> Optional[Bullet]:
        """Get specific bullet by ID"""
        if bullet_id in self.bullet_id_to_index:
            return self.bullets[self.bullet_id_to_index[bullet_id]]
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get playbook statistics"""
        if not self.bullets:
            return {
                "total_bullets": 0,
                "sections": {},
                "helpful_ratio": 0.0,
                "recent_bullets": 0
            }
        
        sections = {}
        total_helpful = 0
        total_harmful = 0
        recent_count = 0
        now = datetime.now()
        
        for bullet in self.bullets:
            # Count by section
            if bullet.section not in sections:
                sections[bullet.section] = 0
            sections[bullet.section] += 1
            
            # Count helpful/harmful
            total_helpful += bullet.helpful
            total_harmful += bullet.harmful
            
            # Count recent bullets (last 7 days)
            try:
                created = datetime.fromisoformat(bullet.created_at)
                if (now - created).days <= 7:
                    recent_count += 1
            except:
                pass
        
        return {
            "total_bullets": len(self.bullets),
            "sections": sections,
            "helpful_ratio": total_helpful / max(total_helpful + total_harmful, 1),
            "recent_bullets": recent_count,
            "total_helpful": total_helpful,
            "total_harmful": total_harmful
        }
    
    def save_playbook(self):
        """Save playbook to files"""
        print(f"   💾 Saving playbook to files...")
        
        # Save metadata
        metadata = {
            "bullets": [bullet.to_dict() for bullet in self.bullets],
            "last_updated": datetime.now().isoformat(),
            "total_bullets": len(self.bullets)
        }
        
        print(f"      📄 Saving metadata to {self.metadata_file}")
        with open(self.metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f"      ✅ Metadata saved with {len(self.bullets)} bullets")
        
        # Save markdown playbook
        print(f"      📝 Saving markdown playbook to {self.playbook_file}")
        with open(self.playbook_file, 'w') as f:
            f.write("# ACE Playbook\n\n")
            f.write(f"Last updated: {datetime.now().isoformat()}\n")
            f.write(f"Total bullets: {len(self.bullets)}\n\n")
            
            # Group by section
            sections = {}
            for bullet in self.bullets:
                if bullet.section not in sections:
                    sections[bullet.section] = []
                sections[bullet.section].append(bullet)
            
            for section, bullets in sections.items():
                f.write(f"## {section}\n\n")
                for bullet in bullets:
                    f.write(f"{bullet.to_markdown()}\n\n")
        print(f"      ✅ Markdown playbook saved")
        
        # Save FAISS index
        print(f"      🔍 Saving FAISS index to {self.embeddings_file}")
        faiss.write_index(self.index, self.embeddings_file)
        print(f"      ✅ FAISS index saved with {self.index.ntotal} vectors")
        
        # Verify files were created
        files_created = []
        if os.path.exists(self.metadata_file):
            files_created.append("metadata.json")
        if os.path.exists(self.playbook_file):
            files_created.append("playbook.md")
        if os.path.exists(self.embeddings_file):
            files_created.append("embeddings.faiss")
        
        print(f"   🎯 Playbook saved successfully! Files created: {', '.join(files_created)}")
    
    def load_playbook(self):
        """Load playbook from files"""
        if not os.path.exists(self.metadata_file):
            print(f"   ❌ No existing playbook found at {self.metadata_file}")
            print(f"   🆕 Starting with empty playbook")
            return
        
        print(f"   📥 Loading existing playbook from {self.metadata_file}")
        
        try:
            with open(self.metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Load bullets
            self.bullets = []
            for bullet_data in metadata.get("bullets", []):
                bullet = Bullet(**bullet_data)
                self.bullets.append(bullet)
            
            print(f"   ✅ Loaded {len(self.bullets)} bullets from metadata")
            
            # Rebuild bullet_id_to_index mapping after loading bullets
            self.bullet_id_to_index = {}
            for i, bullet in enumerate(self.bullets):
                self.bullet_id_to_index[bullet.id] = i
            print(f"   🔧 Rebuilt bullet_id_to_index mapping with {len(self.bullet_id_to_index)} entries")
            
            # Try to load existing FAISS index first
            if os.path.exists(self.embeddings_file):
                print(f"   📥 Loading existing FAISS index from {self.embeddings_file}")
                try:
                    self.index = faiss.read_index(self.embeddings_file)
                    print(f"   ✅ FAISS index loaded with {self.index.ntotal} vectors")
                except Exception as e:
                    print(f"   ⚠️ Failed to load FAISS index: {e}")
                    print(f"   🔄 Rebuilding FAISS index...")
                    self._rebuild_index()
            else:
                print(f"   ⚠️ FAISS index file missing: {self.embeddings_file}")
                print(f"   🔄 Rebuilding FAISS index...")
                self._rebuild_index()
            
            print(f"   🎯 Playbook loaded successfully with {len(self.bullets)} bullets")
            
        except Exception as e:
            print(f"   ❌ Error loading playbook: {e}")
            self.bullets = []
            self.bullet_id_to_index = {}


# Global playbook manager instance
playbook_manager = PlaybookManager()
