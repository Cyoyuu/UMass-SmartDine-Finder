# recommendation.py
import json
import re
import sys
import os
from datetime import datetime, date
from collections import defaultdict
from pathlib import Path
from generator import Generator

from django.utils import timezone

# Load environment variables from .env file using python-dotenv
from dotenv import load_dotenv

# Load .env file from project root
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

# Add umass-toolkit to Python path if not already installed
_umass_toolkit_path = os.path.join(os.path.dirname(__file__), 'umass-toolkit')
if os.path.exists(_umass_toolkit_path) and _umass_toolkit_path not in sys.path:
    sys.path.insert(0, _umass_toolkit_path)
from umass_toolkit.dining import get_locations, get_menu

with open("lm_config.json", "r") as f:
    lm_config = json.load(f)
    generator = Generator(lm_source=lm_config['lm_source'], lm_id=lm_config['lm_id'], max_tokens=4096, temperature=0.2)

DINING_SLUGS = ["berkshire", "worcester", "franklin", "hampshire"]


# ------------------------------------------------------------
# Time-based meal filtering
# ------------------------------------------------------------
def _current_meal_keys():
    """Return meal keys based on local time."""
    now = timezone.localtime()
    hour = now.hour

    if 7 <= hour < 11:
        return ["breakfast", "grabngo"]
    elif 11 <= hour < 16:
        return ["lunch", "grabngo"]
    elif 16 <= hour < 21:
        return ["dinner"]
    elif 21 <= hour <= 23:
        return ["late night"]
    return []


# ------------------------------------------------------------
# Map slug → location ID
# ------------------------------------------------------------
def _map_slug_to_location_id():
    if get_locations is None:
        # Fallback mapping if umass_toolkit is not available
        return {
            "berkshire": 1,
            "worcester": 2,
            "franklin": 3,
            "hampshire": 4
        }
    
    locations = get_locations()
    mapping = {}

    for slug in DINING_SLUGS:
        for loc in locations:
            if slug.lower() in loc["name"].lower():
                mapping[slug] = loc["id"]
                break

    return mapping


# ------------------------------------------------------------
# Extract dish name safely
# ------------------------------------------------------------
def _extract_name(d):
    if "dish-name" in d and isinstance(d["dish-name"], str):
        return d["dish-name"].strip()

    for key in ["item_name", "name", "item", "title"]:
        if key in d and isinstance(d[key], str):
            return d[key].strip()

    return "Unnamed Dish"


# ------------------------------------------------------------
# Hard filters
# ------------------------------------------------------------
def _allergen_conflict(dish, avoid_list):
    allergens = dish.get("allergens") or []
    allergens = [a.lower() for a in allergens]

    for avoid in avoid_list:
        avoid = avoid.lower()
        for al in allergens:
            if avoid in al:
                return True
    return False


def _ingredient_conflict(dish, banned_terms):
    text = " ".join([
        _extract_name(dish),
        " ".join(dish.get("ingredient-list") or [])
    ]).lower()

    return any(term.lower() in text for term in banned_terms)


# ------------------------------------------------------------
# Filter meals by time & user prefs
# ------------------------------------------------------------
def _filter_menu_by_time_and_prefs(full_menu, prefs):
    allowed_meals = set(_current_meal_keys())
    avoid_allergens = prefs.get("avoid_allergens") or []
    avoid_ingredients = prefs.get("avoid_ingredients") or []
    avoid_keywords = prefs.get("avoid_keywords") or []

    banned_terms = list(set(avoid_ingredients + avoid_keywords))

    filtered = {}

    for slug, dishes in full_menu.items():
        hall_candidates = []

        for d in dishes:
            meal = d.get("meal-name") or d.get("meal_name") or ""
            if meal.lower() not in allowed_meals:
                continue

            # HARD FILTER 1: allergens
            if _allergen_conflict(d, avoid_allergens):
                continue

            # HARD FILTER 2: ingredients / keywords
            if _ingredient_conflict(d, banned_terms):
                continue

            hall_candidates.append({
                "name": _extract_name(d),
                "meal": meal,
                "category": d.get("category-name"),
                "allergens": d.get("allergens") or [],
                "diets": d.get("diets") or [],
            })

        filtered[slug] = hall_candidates[:25]  # limit to reduce tokens

    return filtered


# ------------------------------------------------------------
# Extract JSON from LLM response
# ------------------------------------------------------------
def _extract_json(raw):
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    matches = re.findall(r"\{.*\}", raw, flags=re.DOTALL)
    for m in matches:
        try:
            return json.loads(m)
        except Exception:
            continue
    return {}


# ------------------------------------------------------------
# Call LLM to rank dishes
# ------------------------------------------------------------
def _rank_with_llm(mood_text, prefs, candidates):
    prefs_json = json.dumps(prefs, indent=2)
    cands_json = json.dumps(candidates, indent=2)

    prompt = f"""
You are the UMass Dining recommendation engine.

The user stored preferences:
{prefs_json}

User's current mood/request:
\"\"\"{mood_text}\"\"\"

These dishes are available NOW (after time-based filtering + allergen filtering):
{cands_json}

TASK:
For each hall (berkshire, worcester, franklin, hampshire),
select UP TO 3 dishes that BEST match:
- allergies (must follow strictly)
- diet (e.g., vegetarian)
- user's likes/dislikes
- user's goals
- user's current mood text
Return ONLY valid JSON like:

{{
  "berkshire": ["Dish A", "Dish B"],
  "worcester": [],
  "franklin": ["Dish"],
  "hampshire": []
}}
"""

    raw = generator.generate(prompt, json_mode=True)
    parsed = _extract_json(raw)

    result = {slug: parsed.get(slug, []) for slug in DINING_SLUGS}
    for k in result:
        if not isinstance(result[k], list):
            result[k] = []
        result[k] = [str(x) for x in result[k]]
    return result


# ------------------------------------------------------------
# MAIN PUBLIC FUNCTION
# ------------------------------------------------------------
def get_recommendations_for_all_dining(mood_text, stored_preferences, menu_data=None):
    """
    Get recommendations for all dining halls.
    
    Args:
        mood_text: User's request/mood text
        stored_preferences: User preferences dict
        menu_data: Optional pre-formatted menu data (from database).
                   If None, will fetch from umass_toolkit API.
    
    Returns:
        Dict mapping hall slugs to list of recommended dish names
    """
    if menu_data is not None:
        # Use provided menu data (from database)
        full_menu = menu_data
    else:
        # Fetch from umass_toolkit API (original behavior)
        if get_menu is None:
            raise ImportError(
                "umass_toolkit is not available and no menu_data provided. "
                "Either install umass_toolkit or provide menu_data parameter."
            )
        slug_to_id = _map_slug_to_location_id()
        today = timezone.localdate()

        # Fetch full raw menu
        full_menu = {}
        for slug in DINING_SLUGS:
            full_menu[slug] = get_menu(slug_to_id[slug], date=today)

    # Hard filter
    candidates = _filter_menu_by_time_and_prefs(full_menu, stored_preferences)

    # LLM ranking
    return _rank_with_llm(mood_text, stored_preferences, candidates)
