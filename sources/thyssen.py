from typing import List, Optional
from .generic_scraper import scrape_from_listing
from mc_utils.model import Event

def scrape_thyssen(exhibitions_url: str, activities_url: str, tickets_url: Optional[str], institution_id: str, institution_name: str) -> List[Event]:
    evs: List[Event] = []
    if exhibitions_url:
        evs += scrape_from_listing(exhibitions_url, "exhibition", institution_name, institution_id, tickets_url, hint="/exposiciones")
    if activities_url:
        evs += scrape_from_listing(activities_url, "activity", institution_name, institution_id, tickets_url, hint="/actividades")
    return evs
