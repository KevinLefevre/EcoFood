from datetime import datetime, timedelta
from typing import Any, Dict, Optional, List
import json
import hashlib

class ProfileCache:
    def __init__(self, ttl_minutes: int = 60):
        self._cache: Dict[str, tuple[datetime, Dict[str, Any]]] = {}
        self._ttl = timedelta(minutes=ttl_minutes)

    def _generate_key(self, members: List[Dict[str, Any]]) -> str:
        # Sort members to ensure consistent key
        # We assume members list contains dicts with at least a 'name' field
        try:
            serialized = json.dumps(
                sorted(members, key=lambda x: str(x.get("name", ""))), 
                sort_keys=True,
                default=str
            )
            return hashlib.sha256(serialized.encode()).hexdigest()
        except Exception:
            # Fallback for unhashable content
            return ""

    def get(self, members: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        key = self._generate_key(members)
        if not key:
            return None
            
        if key in self._cache:
            timestamp, data = self._cache[key]
            if datetime.now() - timestamp < self._ttl:
                return data
            else:
                del self._cache[key]
        return None

    def set(self, members: List[Dict[str, Any]], profile: Dict[str, Any]) -> None:
        key = self._generate_key(members)
        if key:
            self._cache[key] = (datetime.now(), profile)

# Global instance
profile_cache = ProfileCache()
