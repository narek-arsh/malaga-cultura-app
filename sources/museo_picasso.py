from typing import List, Optional
from urllib.parse import urlparse
from .generic_scraper import scrape_from_listing
from mc_utils.model import Event

def scrape_mpm(base_url: str, exhibitions_url: str, activities_url: str, tickets_url: Optional[str], institution_id: str, institution_name: str) -> List[Event]:
    # Exhibitions: use base_url (home has cards) and also filter by '/exposiciones/'
    evs = []
    evs += scrape_from_listing(base_url, "exhibition", institution_name, institution_id, tickets_url, hint="/exposiciones/")
    # Activities: their activities live under tickets subdomain; scrape activities_url broadly
    if activities_url:
        evs += scrape_from_listing(activities_url, "activity", institution_name, institution_id, tickets_url, hint="")
    return evs
