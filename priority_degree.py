import requests

def fetch_api_priorities(query):
    """
    Fetches related words and their scores from the DataMuse API.
    Returns a dictionary: { word: score }
    """
    try:
        # DataMuse API: sug?s=query returns suggestions with scores
        url = f"https://api.datamuse.com/sug?s={query}"
        response = requests.get(url, timeout=2) # 2 second timeout to prevent hanging
        if response.status_code == 200:
            data = response.json()
            # Convert to dictionary {word: score}
            # DataMuse returns [{'word': 'foo', 'score': 123}, ...]
            priority_map = {item['word'].lower(): item['score'] for item in data}
            return priority_map
    except Exception as e:
        print(f"Error fetching API priorities: {e}")
    
    return {}

# ---------- SEARCH LOGIC WITH OOP: Inheritance & Polymorphism ----------

class CareerSuggester:
    """Average base class for suggesting careers."""
    def suggest(self, query):
        """
        Base suggest method.
        """
        return []

class PriorityCareerSuggester(CareerSuggester):
    """
    Subclass that provides suggestions sorted by priority using API data.
    """
    def suggest_with_api(self, candidates, query):
        """
        Takes a list of candidate dictionaries (from DB) and sorts them
        based on scores fetched from the API.
        
        candidates: List of dicts, e.g., [{'keyword': 'Engineer', ...}, ...]
        query: The user's search query
        """
        # 1. Fetch scores from API
        api_scores = fetch_api_priorities(query)
        
        # 2. Enrich candidates with score
        enriched_candidates = []
        for cand in candidates:
            keyword = cand.get("keyword", "").lower().strip()
            
            # Match logic:
            # Check if the FULL keyword is in API results
            score = api_scores.get(keyword, 0)
            
            # If not found or low score, check constituent words
            # e.g., if query="soft", API has "software": 500
            # candidate="software engineer" should get 500
            if score == 0:
                words = keyword.split()
                for w in words:
                    w_score = api_scores.get(w, 0)
                    if w_score > score:
                        score = w_score
            
            cand["api_score"] = score
            enriched_candidates.append(cand)
            
        # 3. Sort by priority (api_score) in descending order
        sorted_candidates = sorted(
            enriched_candidates, 
            key=lambda x: x["api_score"], 
            reverse=True
        )
        
        return sorted_candidates

def get_priority_suggestions(candidates, query):
    """
    Helper function to use the PriorityCareerSuggester.
    Now takes full candidates list from DB.
    """
    suggester = PriorityCareerSuggester()
    return suggester.suggest_with_api(candidates, query)
