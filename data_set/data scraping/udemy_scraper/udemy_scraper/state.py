"""
State Management - حفظ الـ Progress و Resume
"""
import json
from pathlib import Path
from threading import Lock


class State:
    def __init__(self, state_file: str):
        self.state_file = Path(state_file)
        self.lock = Lock()
        self.data = self._load()
        self._cached_seen = set(str(x) for x in self.data["seen_course_ids"])
    
    def _load(self):
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {
            "completed_filters": [],
            "seen_course_ids": [],
            "filter_progress": {},
        }
    
    def save(self):
        with self.lock:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            self.state_file.write_text(
                json.dumps(self.data, indent=2),
                encoding="utf-8"
            )
    
    def is_seen(self, course_id) -> bool:
        return str(course_id) in self._cached_seen
    
    def add_seen(self, course_id):
        with self.lock:
            cid = str(course_id)
            if cid not in self._cached_seen:
                self.data["seen_course_ids"].append(cid)
                self._cached_seen.add(cid)
    
    def is_filter_complete(self, filter_key: str) -> bool:
        return filter_key in self.data["completed_filters"]
    
    def mark_filter_complete(self, filter_key: str):
        with self.lock:
            if filter_key not in self.data["completed_filters"]:
                self.data["completed_filters"].append(filter_key)
            self.data["filter_progress"].pop(filter_key, None)
    
    def get_progress(self, filter_key: str) -> int:
        return self.data["filter_progress"].get(filter_key, 0)
    
    def set_progress(self, filter_key: str, page: int):
        with self.lock:
            self.data["filter_progress"][filter_key] = page
    
    def stats(self):
        return {
            "total_seen": len(self.data["seen_course_ids"]),
            "completed_filters": len(self.data["completed_filters"]),
        }