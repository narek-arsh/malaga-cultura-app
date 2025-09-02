from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
import hashlib
from datetime import datetime

def sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()

@dataclass
class Event:
    id: str
    type: str  # "exhibition" | "activity" | "permanent"
    institution: str
    institution_id: str
    title: str
    description: Optional[str]
    image_url: Optional[str]
    detail_url: Optional[str]
    tickets_url: Optional[str]
    status: str  # "scheduled" | "cancelled" | "postponed" | "ongoing"
    date_start: Optional[str]        # "YYYY-MM-DD" (for exhibitions)
    date_end: Optional[str]
    datetime_start: Optional[str]    # "YYYY-MM-DDTHH:MM:SS+02:00" (for activities)
    datetime_end: Optional[str]
    price: Optional[str]
    first_seen: Optional[str]
    last_seen: Optional[str]
    last_changed: Optional[str]
    source: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

def make_event_id(detail_url: Optional[str], institution_id: str, title: str) -> str:
    base = (detail_url or "") + "|" + institution_id + "|" + title.strip().lower()
    return sha1(base)

def now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"
