"""
Core logic for SmartBite AI.

Features:
- Local recipe dataset matching
- Gemini AI recipe generation
- Tavily recipe web search
- Tavily YouTube tutorial search
- Ingredient matching
- Shopping list generation
"""

import os
import json
import re

import streamlit as st
from dotenv import load_dotenv
from tavily import TavilyClient
from google import genai


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

load_dotenv()


def _get_secret(key: str) -> str:
    """Get value from Streamlit secrets or environment."""

    try:
        if key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass

    return os.getenv(key, "")


GEMINI_API_KEY = _get_secret("GEMINI_API_KEY")
TAVILY_API_KEY = _get_secret("TAVILY_API_KEY")


# ============================================================
# GEMINI CLIENT
# ============================================================

gemini_client = None

if GEMINI_API_KEY:
    try:
        gemini_client = genai.Client(
            api_key=GEMINI_API_KEY
        )
    except Exception as e:
        print(f"GEMINI CLIENT ERROR: {e}")


# ============================================================
# TAVILY CLIENT
# ============================================================

tavily_client = None

if TAVILY_API_KEY:
    try:
        tavily_client = TavilyClient(
            api_key=TAVILY_API_KEY
        )
    except Exception as e:
        print(f"TAVILY CLIENT ERROR: {e}")


# ============================================================
# LOCAL RECIPE DATASET
# ============================================================

RECIPES_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "recipes.json"
)


@st.cache_data(show_spinner=False)
def load_local_recipes() -> list:
    """Load recipes.json."""

    try:
        with open(
            RECIPES_PATH,
            "r",
            encoding="utf-8"
        ) as f:
            data = json.load(f)

        if isinstance(data, list):
            return data

        return []

    except (
        FileNotFoundError,
        json.JSONDecodeError
    ):
        return []


LOCAL_RECIPES = load_local_recipes()


# ============================================================
# NORMALIZATION
# ============================================================

def _normalize(text: str) -> str:

    if text is None:
        return ""

    return str(text).strip().lower()


# ============================================================
# PARSE USER INGREDIENTS
# ============================================================

def _parse_user_ingredients(
    ingredients: str
) -> list:

    if not ingredients:
        return []

    result = []

    for item in ingredients.split(","):

        item = _normalize(item)

        if item:
            result.append(item)

    return result


# ============================================================
# INGREDIENT ALIASES
# ============================================================

INGREDIENT_ALIASES = {
    "tomatoes": "tomato",
    "onions": "onion",
    "potatoes": "potato",
    "carrots": "carrot",
    "eggs": "egg",
    "chillies": "chili",
    "chilies": "chili",
    "capsicums": "capsicum",
    "bell pepper": "capsicum",
    "bell peppers": "capsicum",
}


def _canonical_ingredient(
    ingredient: str
) -> str:

    ingredient = _normalize(
        ingredient
    )

    if ingredient in INGREDIENT_ALIASES:
        return INGREDIENT_ALIASES[
            ingredient
        ]

    # Simple plural handling

    if ingredient.endswith("ies"):
        ingredient = (
            ingredient[:-3] + "y"
        )

    elif ingredient.endswith("es"):
        ingredient = ingredient[:-2]

    elif (
        ingredient.endswith("s")
        and not ingredient.endswith("ss")
    ):
        ingredient = ingredient[:-1]

    return ingredient


# ============================================================
# INGREDIENT MATCHING
# ============================================================

def _ingredients_match(
    user_item: str,
    recipe_item: str
) -> bool:

    user_item = _canonical_ingredient(
        user_item
    )

    recipe_item = _canonical_ingredient(
        recipe_item
    )

    if not user_item or not recipe_item:
        return False

    if user_item == recipe_item:
        return True

    user_words = set(
        user_item.split()
    )

    recipe_words = set(
        recipe_item.split()
    )

    common = (
        user_words & recipe_words
    )

    for word in common:
        if len(word) >= 4:
            return True

    return False


# ============================================================
# SCORE RECIPE
# ============================================================

def _score_recipe(
    user_ings: list,
    recipe: dict
) -> tuple:
    """
    Return:

    score
    matched ingredients
    missing ingredients
    """

    recipe_ings = recipe.get(
        "ingredients",
        []
    )

    if not isinstance(
        recipe_ings,
        list
    ):
        return 0.0, [], []

    recipe_ings = [
        str(item).strip()
        for item in recipe_ings
        if str(item).strip()
    ]

    if not recipe_ings:
        return 0.0, [], []

    matched = []
    missing = []

    for recipe_item in recipe_ings:

        found = False

        for user_item in user_ings:

            if _ingredients_match(
                user_item,
                recipe_item
            ):
                found = True
                break

        if found:
            matched.append(
                recipe_item
            )
        else:
            missing.append(
                recipe_item
            )

    score = (
        len(matched)
        / len(recipe_ings)
    )

    return (
        score,
        matched,
        missing
    )


# ============================================================
# FILTER RECIPES
# ============================================================

def _passes_filters(
    recipe: dict,
    cuisine: str,
    diet: str,
    time_minutes: int
) -> bool:

    # Cuisine filter

    if (
        cuisine
        and cuisine.lower() != "any"
    ):

        recipe_cuisine = _normalize(
            recipe.get(
                "cuisine",
                ""
            )
        )

        if recipe_cuisine != _normalize(
            cuisine
        ):
            return False

    # Diet filter

    if (
        diet
        and diet.lower() != "none"
    ):

        tags = [
            _normalize(tag)
            for tag in recipe.get(
                "dietary_tags",
                []
            )
        ]

        if _normalize(diet) not in tags:
            return False

    # Time filter

    recipe_time = recipe.get(
        "cooking_time"
    )

    try:
        recipe_time = int(
            recipe_time
        )
    except (
        TypeError,
        ValueError
    ):
        recipe_time = None

    if (
        recipe_time is not None
        and time_minutes
        and recipe_time > time_minutes
    ):
        return False

    return True


# ============================================================
# FORMAT LOCAL RECIPE
# ============================================================

def _format_local_recipe(
    recipe: dict,
    matched: list,
    missing: list
) -> dict:

    all_ingredients = recipe.get(
        "ingredients",
        []
    )

    return {
        "recipe_name": recipe.get(
            "name",
            "Recipe"
        ),

        "estimated_time_minutes":
            recipe.get(
                "cooking_time",
                20
            ),

        # Keep ALL recipe ingredients
        "ingredients_used":
            all_ingredients,

        # Keep matched separately
        "matched_ingredients":
            matched,

        "missing_ingredients":
            missing,

        "steps":
            recipe.get(
                "steps",
                []
            ),

        "cuisine":
            recipe.get(
                "cuisine",
                ""
            ),

        "difficulty":
            recipe.get(
                "difficulty",
                "Easy"
            ),

        "servings":
            recipe.get(
                "servings",
                2
            ),

        "description":
            recipe.get(
                "description",
                ""
            ),

        "image":
            recipe.get(
                "image",
                recipe.get(
                    "image_url",
                    ""
                )
            ),
    }


# ============================================================
# SEARCH LOCAL RECIPES
# ============================================================

def search_local_recipes(
    ingredients: str,
    cuisine: str,
    time_minutes: int,
    diet: str,
    min_score: float = 0.25,
    max_results: int = 3
) -> list:

    user_ings = _parse_user_ingredients(
        ingredients
    )

    if (
        not user_ings
        or not LOCAL_RECIPES
    ):
        return []

    scored = []

    for recipe in LOCAL_RECIPES:

        if not _passes_filters(
            recipe,
            cuisine,
            diet,
            time_minutes
        ):
            continue

        score, matched, missing = (
            _score_recipe(
                user_ings,
                recipe
            )
        )

        if score >= min_score:

            scored.append(
                (
                    score,
                    recipe,
                    matched,
                    missing
                )
            )

    scored.sort(
        key=lambda x: x[0],
        reverse=True
    )

    return [
        _format_local_recipe(
            recipe,
            matched,
            missing
        )
        for (
            score,
            recipe,
            matched,
            missing
        )
        in scored[:max_results]
    ]


# ============================================================
# GEMINI PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are SmartBite AI, a practical recipe assistant.

Available ingredients:
{ingredients}

Cuisine preference:
{cuisine}

Maximum cooking time:
{time} minutes

Servings:
{servings}

Dietary preference:
{diet}

Generate 1 to 3 realistic recipes.

Requirements:

1. Use the available ingredients as much as possible.
2. Respect the cuisine preference.
3. Respect the dietary preference.
4. Do not exceed the cooking time.
5. Use simple ingredients.
6. Clearly identify ingredients used.
7. Clearly identify missing ingredients.
8. Give simple step-by-step instructions.
9. Make the recipes suitable for beginners.

Return ONLY valid JSON.

Format:

{{
    "recipes": [
        {{
            "recipe_name": "Recipe name",
            "estimated_time_minutes": 20,
            "ingredients_used": [
                "rice",
                "egg",
                "onion"
            ],
            "missing_ingredients": [
                "soy sauce"
            ],
            "steps": [
                "Step 1",
                "Step 2",
                "Step 3"
            ]
        }}
    ],
    "note": ""
}}
"""


# ============================================================
# GEMINI GENERATION
# ============================================================

def _generate_recipe_gemini(
    ingredients: str,
    cuisine: str,
    time_minutes: int,
    servings: int,
    diet: str
) -> dict:

    if not gemini_client:

        return {
            "recipes": [],
            "note":
                "Gemini API key is not configured."
        }

    prompt = SYSTEM_PROMPT.format(
        ingredients=ingredients,
        cuisine=cuisine,
        time=time_minutes,
        servings=servings,
        diet=diet
    )

    try:

        response = (
            gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
        )

        raw_text = response.text.strip()

        # Remove ```json ... ``` if Gemini returns it

        if raw_text.startswith("```"):

            raw_text = re.sub(
                r"^```(?:json)?",
                "",
                raw_text,
                flags=re.IGNORECASE
            )

            raw_text = re.sub(
                r"```$",
                "",
                raw_text
            )

            raw_text = raw_text.strip()

        data = json.loads(
            raw_text
        )

        if not isinstance(
            data,
            dict
        ):

            return {
                "recipes": [],
                "note":
                    "Gemini returned an invalid response."
            }

        if "recipes" not in data:
            data["recipes"] = []

        return data

    except Exception as e:

        print(
            f"GEMINI ERROR: {e}"
        )

        return {
            "recipes": [],
            "note":
                "Gemini could not generate the recipe. "
                "Please try again."
        }


# ============================================================
# PUBLIC RECIPE FUNCTION
# ============================================================

def generate_recipe(
    ingredients: str,
    cuisine: str,
    time_minutes: int,
    servings: int,
    diet: str
) -> dict:

    # First: local dataset

    local_matches = search_local_recipes(
        ingredients,
        cuisine,
        time_minutes,
        diet
    )

    if local_matches:

        return {
            "recipes": local_matches,
            "note":
                "Matched from our curated recipe collection."
        }

    # Second: Gemini

    return _generate_recipe_gemini(
        ingredients,
        cuisine,
        time_minutes,
        servings,
        diet
    )


# ============================================================
# SHOPPING LIST
# ============================================================

def build_shopping_list(
    recipes: list
) -> list:

    shopping_list = []

    for recipe in recipes:

        for item in recipe.get(
            "missing_ingredients",
            []
        ):

            item = str(
                item
            ).strip()

            if not item:
                continue

            exists = any(
                item.lower()
                == existing.lower()
                for existing
                in shopping_list
            )

            if not exists:
                shopping_list.append(
                    item
                )

    return shopping_list


# ============================================================
# TAVILY RECIPE SEARCH
# ============================================================

@st.cache_data(
    show_spinner=False,
    ttl=3600
)
def search_recipes(
    cuisine: str,
    ingredients: str,
    max_results: int = 3
) -> list:

    if not tavily_client:
        return []

    query = (
        f"{cuisine} recipe using "
        f"{ingredients}"
    ).strip()

    try:

        response = tavily_client.search(
            query=query,
            max_results=max_results
        )

        results = []

        for result in response.get(
            "results",
            []
        ):

            url = result.get(
                "url",
                ""
            )

            if url:

                results.append({
                    "title":
                        result.get(
                            "title",
                            "Recipe"
                        ),
                    "url": url
                })

        return results

    except Exception as e:

        print(
            f"TAVILY DEBUG ERROR: {e}"
        )

        return []


# ============================================================
# TAVILY YOUTUBE SEARCH
# ============================================================

@st.cache_data(
    show_spinner=False,
    ttl=3600
)
def search_youtube_videos(
    recipe_name: str,
    max_results: int = 2
) -> list:

    if (
        not tavily_client
        or not recipe_name
    ):
        return []

    query = (
        f"{recipe_name} recipe tutorial"
    )

    try:

        response = tavily_client.search(
            query=query,
            max_results=max_results,
            include_domains=[
                "youtube.com"
            ]
        )

        results = []

        for result in response.get(
            "results",
            []
        ):

            url = result.get(
                "url",
                ""
            )

            if url:

                results.append({
                    "title":
                        result.get(
                            "title",
                            "Watch on YouTube"
                        ),
                    "url": url
                })

        return results

    except Exception as e:

        print(
            f"TAVILY YOUTUBE DEBUG ERROR: {e}"
        )

        return []
