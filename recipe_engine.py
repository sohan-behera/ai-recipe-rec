"""
Core logic for the AI Recipe & Meal Recommendation Assistant.
Keeps Gemini + Groq + Tavily calls separate from the Streamlit UI.

Recipe lookup strategy:
1. Try to match against the local recipes.json dataset first (fast, free, always accurate).
2. If nothing in the local dataset matches well enough, ask Gemini.
3. If Gemini fails (e.g. quota exceeded), fall back to Groq.
4. If both AI providers fail, fall back again to a relaxed local search
   instead of showing a raw API error to the user.
"""

import os
import json
import streamlit as st
import google.generativeai as genai
from groq import Groq
from tavily import TavilyClient
from dotenv import load_dotenv

load_dotenv()


def _get_secret(key: str) -> str:
    """Read a key from Streamlit Cloud secrets if available, else from the local .env file."""
    try:
        import streamlit as st
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key, "")


GEMINI_API_KEY = _get_secret("GEMINI_API_KEY")
GROQ_API_KEY = _get_secret("GROQ_API_KEY")
TAVILY_API_KEY = _get_secret("TAVILY_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-3.6-flash")

groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

tavily_client = TavilyClient(api_key=TAVILY_API_KEY) if TAVILY_API_KEY else None


# ---------------------------------------------------------------------------
# Local dataset loading
# ---------------------------------------------------------------------------

RECIPES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recipes.json")


@st.cache_data(show_spinner=False)
def load_local_recipes() -> list:
    """Load the local recipes.json dataset. Returns [] if missing or invalid."""
    try:
        with open(RECIPES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


LOCAL_RECIPES = load_local_recipes()


def _normalize(text: str) -> str:
    return text.strip().lower()


def _parse_user_ingredients(ingredients: str) -> list:
    return [_normalize(i) for i in ingredients.split(",") if i.strip()]


def _score_recipe(user_ings: list, recipe: dict) -> tuple:
    """Return (score 0-1, matched_ingredients, missing_ingredients) for a recipe."""
    recipe_ings = [_normalize(i) for i in recipe.get("ingredients", [])]
    if not recipe_ings:
        return 0.0, [], []

    matched = [ri for ri in recipe_ings if any(ui in ri or ri in ui for ui in user_ings)]
    missing = [ri for ri in recipe_ings if ri not in matched]
    score = len(matched) / len(recipe_ings)
    return score, matched, missing


def _passes_filters(recipe: dict, cuisine: str, diet: str, time_minutes: int) -> bool:
    if cuisine and cuisine.lower() != "any" and _normalize(recipe.get("cuisine", "")) != _normalize(cuisine):
        return False

    if diet and diet.lower() != "none":
        tags = [_normalize(t) for t in recipe.get("dietary_tags", [])]
        if _normalize(diet) not in tags:
            return False

    recipe_time = recipe.get("cooking_time")
    if isinstance(recipe_time, (int, float)) and time_minutes and recipe_time > time_minutes:
        return False

    return True


def _format_local_recipe(recipe: dict, matched: list, missing: list) -> dict:
    """Convert a local dataset recipe into the same schema the UI expects from Gemini/Groq."""
    return {
        "recipe_name": recipe.get("name", "Recipe"),
        "estimated_time_minutes": recipe.get("cooking_time", "?"),
        "ingredients_used": matched,
        "missing_ingredients": missing,
        "steps": recipe.get("steps", []),
    }


def search_local_recipes(ingredients: str, cuisine: str, time_minutes: int, diet: str,
                          min_score: float = 0.4, max_results: int = 3) -> list:
    """Find recipes from the local dataset that reasonably match the user's ingredients."""
    user_ings = _parse_user_ingredients(ingredients)
    if not user_ings or not LOCAL_RECIPES:
        return []

    scored = []
    for recipe in LOCAL_RECIPES:
        if not _passes_filters(recipe, cuisine, diet, time_minutes):
            continue
        score, matched, missing = _score_recipe(user_ings, recipe)
        if score >= min_score:
            scored.append((score, recipe, matched, missing))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [_format_local_recipe(r, m, mi) for _, r, m, mi in scored[:max_results]]


# ---------------------------------------------------------------------------
# Shared prompt used by BOTH Gemini and Groq, so the output schema matches
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a helpful, practical recipe assistant for students with limited cooking experience.

Context:
- Available ingredients: {ingredients}
- Cuisine preference: {cuisine}
- Cooking time available: {time} minutes
- Servings needed: {servings}
- Dietary preference: {diet}

Task:
Suggest 1 to 3 simple, realistic recipes that best use the available ingredients, respecting the
cuisine, time, servings, and dietary preference given above.

Constraints:
- Only suggest recipes that are realistic to cook within the given time.
- Clearly separate ingredients the user already has from ingredients they are missing.
- Do not invent exotic ingredients or techniques a beginner cannot handle.
- If the given ingredients are too limited to make a reasonable dish, say so honestly instead of
  forcing a recipe, and suggest the minimum additional ingredients needed.

Output format:
Return ONLY valid JSON (no markdown, no commentary) matching this schema:
{{
  "recipes": [
    {{
      "recipe_name": "string",
      "estimated_time_minutes": number,
      "ingredients_used": ["string", ...],
      "missing_ingredients": ["string", ...],
      "steps": ["string", ...]
    }}
  ],
  "note": "string (empty if nothing to add)"
}}
"""


def _clean_json_text(raw_text: str) -> str:
    """Strip markdown code fences some models add despite instructions not to."""
    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.lower().startswith("json"):
            raw_text = raw_text[4:].strip()
    return raw_text


# ---------------------------------------------------------------------------
# Gemini provider
# ---------------------------------------------------------------------------

def _generate_recipe_gemini(ingredients: str, cuisine: str, time_minutes: int, servings: int, diet: str) -> dict:
    """Call Gemini to generate recipe suggestions. Raises on failure so the
    caller can fall back to the next provider."""
    prompt = SYSTEM_PROMPT.format(
        ingredients=ingredients,
        cuisine=cuisine,
        time=time_minutes,
        servings=servings,
        diet=diet,
    )

    response = model.generate_content(prompt)
    raw_text = _clean_json_text(response.text)

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        return {"recipes": [], "note": "Sorry, I couldn't parse a recipe this time. Please try again."}


# ---------------------------------------------------------------------------
# Groq provider (backup AI, OpenAI-compatible chat completion API)
# ---------------------------------------------------------------------------

def _generate_recipe_groq(ingredients: str, cuisine: str, time_minutes: int, servings: int, diet: str) -> dict:
    """Call Groq (Llama 3.3 70B) to generate recipe suggestions. Raises on
    failure so the caller can fall back to the local dataset."""
    if not groq_client:
        raise RuntimeError("Groq API key is not configured.")

    prompt = SYSTEM_PROMPT.format(
        ingredients=ingredients,
        cuisine=cuisine,
        time=time_minutes,
        servings=servings,
        diet=diet,
    )

    completion = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You return only valid JSON, no markdown, no commentary."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
    )

    raw_text = _clean_json_text(completion.choices[0].message.content)

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        return {"recipes": [], "note": "Sorry, I couldn't parse a recipe this time. Please try again."}


# ---------------------------------------------------------------------------
# Public entry point used by app.py
# ---------------------------------------------------------------------------

def generate_recipe(ingredients: str, cuisine: str, time_minutes: int, servings: int, diet: str) -> dict:
    """
    Try the local recipe dataset first. If it doesn't have a good enough match:
        1. Try Gemini.
        2. If Gemini fails (quota, network, etc.), try Groq.
        3. If both AI providers fail, fall back to a relaxed local search
           instead of surfacing a raw API error to the user.
    """
    local_matches = search_local_recipes(ingredients, cuisine, time_minutes, diet)

    if local_matches:
        return {
            "recipes": local_matches,
            "note": "Matched from our curated recipe collection.",
        }

    gemini_error = None
    groq_error = None

    try:
        return _generate_recipe_gemini(ingredients, cuisine, time_minutes, servings, diet)
    except Exception as e:
        gemini_error = e

    try:
        return _generate_recipe_groq(ingredients, cuisine, time_minutes, servings, diet)
    except Exception as e:
        groq_error = e

    # Both AI providers failed - relax the local match threshold and try again
    # so the user still sees something useful instead of a dead end.
    relaxed_matches = search_local_recipes(
        ingredients, cuisine, time_minutes, diet,
        min_score=0.15,
    )

    if relaxed_matches:
        return {
            "recipes": relaxed_matches,
            "note": (
                "Our AI assistant is temporarily unavailable, so here are the "
                "closest matches from our recipe collection instead."
            ),
        }

    print(f"GEMINI ERROR: {gemini_error}")
    print(f"GROQ ERROR: {groq_error}")

    return {
        "recipes": [],
        "note": (
            "Our AI assistant is temporarily unavailable and no close matches "
            "were found in our recipe collection. Please try again in a few minutes "
            "or adjust your ingredients."
        ),
    }


def build_shopping_list(recipes: list) -> list:
    """Combine missing_ingredients across all suggested recipes into one deduplicated shopping list."""
    shopping_list = []
    for recipe in recipes:
        for item in recipe.get("missing_ingredients", []):
            if item.lower() not in [s.lower() for s in shopping_list]:
                shopping_list.append(item)
    return shopping_list


@st.cache_data(show_spinner=False, ttl=3600)
def search_recipes(cuisine: str, ingredients: str, max_results: int = 3) -> list:
    """Optional: use Tavily to find public recipe links as extra source references."""
    if not tavily_client:
        return []

    query = f"{cuisine} recipe using {ingredients}".strip()
    try:
        results = tavily_client.search(query=query, max_results=max_results)
        return [
            {"title": r.get("title", "Recipe"), "url": r.get("url", "")}
            for r in results.get("results", [])
        ]
    except Exception as e:
        print(f"TAVILY DEBUG ERROR: {e}")
        return []


@st.cache_data(show_spinner=False, ttl=3600)
def search_youtube_videos(recipe_name: str, max_results: int = 2) -> list:
    """Use Tavily, restricted to youtube.com, to find video tutorials for a recipe."""
    if not tavily_client or not recipe_name:
        return []

    query = f"{recipe_name} recipe tutorial"
    try:
        results = tavily_client.search(
            query=query,
            max_results=max_results,
            include_domains=["youtube.com"],
        )
        return [
            {"title": r.get("title", "Watch on YouTube"), "url": r.get("url", "")}
            for r in results.get("results", [])
            if r.get("url")
        ]
    except Exception as e:
        print(f"TAVILY YOUTUBE DEBUG ERROR: {e}")
        return []
