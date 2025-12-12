from typing import Dict, List, Optional
from datetime import datetime, timedelta
from tasks.common.types.draft import TaskDraft

class DraftRepository:
    """Draft repository for storing and retrieving task drafts"""
    def __init__(self):
        # user_id -> [draft1, draft2, draft3] (max 3 per user)
        self.user_drafts: Dict[str, List[TaskDraft]] = {}
    
    def _cleanup_expired_drafts(self, user_id: str):
        """Clean up drafts older than 1 hour"""
        if user_id not in self.user_drafts:
            return
        
        one_hour_ago = datetime.now() - timedelta(hours=1)
        self.user_drafts[user_id] = [
            draft for draft in self.user_drafts[user_id] 
            if draft.updated_at > one_hour_ago
        ]
    
    def save_draft(self, draft: TaskDraft, user_id: str = "default_user"):
        """Save draft for user (max 3 per user)"""
        self._cleanup_expired_drafts(user_id)
        
        if user_id not in self.user_drafts:
            self.user_drafts[user_id] = []
        
        # Add to front (most recent first)
        self.user_drafts[user_id].insert(0, draft)
        
        # Keep only 3 most recent drafts
        if len(self.user_drafts[user_id]) > 3:
            self.user_drafts[user_id] = self.user_drafts[user_id][:3]
    
    def get_latest_draft(self, user_id: str = "default_user") -> Optional[TaskDraft]:
        """Get latest draft for user"""
        self._cleanup_expired_drafts(user_id)
        
        if user_id in self.user_drafts and self.user_drafts[user_id]:
            return self.user_drafts[user_id][0]
        return None
    
    def remove_draft(self, draft_id: str, user_id: str = "default_user"):
        """Remove specific draft"""
        if user_id not in self.user_drafts:
            return
        
        self.user_drafts[user_id] = [
            draft for draft in self.user_drafts[user_id] 
            if draft.id != draft_id
        ]
    
    def get_all_drafts(self, user_id: str = "default_user") -> List[TaskDraft]:
        """Get all non-expired drafts for user"""
        self._cleanup_expired_drafts(user_id)
        return self.user_drafts.get(user_id, [])
