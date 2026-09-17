import streamlit as st
from dotenv import load_dotenv

from recipe_engine import (
    generate_recipe,
    build_shopping_list,
    search_recipes,
    search_youtube_videos,
    LOCAL_RECIPES,
    _parse_user_ingredients,
    _score_recipe,
    GEMINI_API_KEY,
    TAVILY_API_KEY,
)

# ===========================================================================
# LOAD ENVIRONMENT
# ===========================================================================

load_dotenv()

GEMINI_READY = bool(GEMINI_API_KEY)
TAVILY_READY = bool(TAVILY_API_KEY)


# ===========================================================================
# PAGE CONFIGURATION
# ===========================================================================

st.set_page_config(
    page_title="SmartBite AI",
    page_icon="🥗",
    layout="wide",
)


# ===========================================================================
# VERIFY NODE
# ===========================================================================

def verify_recipe(recipe, time_minutes, diet):
    """
    Verify Node

    Validates Gemini-generated recipes before
    displaying them to the user.
    """

    # -----------------------------------------------------------------------
    # 1. Check recipe format
    # -----------------------------------------------------------------------

    if not isinstance(recipe, dict):
        return False, "Recipe is not in the correct format."

    # -----------------------------------------------------------------------
    # 2. Check recipe name
    # -----------------------------------------------------------------------

    recipe_name = str(
        recipe.get("recipe_name", "")
    ).strip()

    if not recipe_name:
        return False, "Recipe name is missing."

    # -----------------------------------------------------------------------
    # 3. Check ingredients
    # -----------------------------------------------------------------------

    ingredients = recipe.get(
        "ingredients_used",
        []
    )

    if not isinstance(ingredients, list):
        return False, (
            f"{recipe_name}: ingredients are not "
            "in the correct format."
        )

    if len(ingredients) == 0:
        return False, (
            f"{recipe_name}: ingredients are missing."
        )

    # -----------------------------------------------------------------------
    # 4. Check cooking steps
    # -----------------------------------------------------------------------

    steps = recipe.get(
        "steps",
        []
    )

    if not isinstance(steps, list):
        return False, (
            f"{recipe_name}: cooking steps are not "
            "in the correct format."
        )

    if len(steps) == 0:
        return False, (
            f"{recipe_name}: cooking steps are missing."
        )

    # -----------------------------------------------------------------------
    # 5. Check cooking time
    # -----------------------------------------------------------------------

    estimated_time = recipe.get(
        "estimated_time_minutes"
    )

    try:
        estimated_time = int(
            estimated_time
        )
    except (TypeError, ValueError):
        return False, (
            f"{recipe_name}: invalid cooking time."
        )

    if estimated_time <= 0:
        return False, (
            f"{recipe_name}: cooking time must "
            "be greater than zero."
        )

    if estimated_time > time_minutes:
        return False, (
            f"{recipe_name}: cooking time "
            f"({estimated_time} min) is longer than "
            f"your available time ({time_minutes} min)."
        )

    # -----------------------------------------------------------------------
    # Combine recipe information for diet verification
    # -----------------------------------------------------------------------

    recipe_text = (
        recipe_name
        + " "
        + " ".join(
            str(x)
            for x in ingredients
        )
        + " "
        + " ".join(
            str(x)
            for x in steps
        )
    ).lower()

    # -----------------------------------------------------------------------
    # 6. Vegetarian verification
    # -----------------------------------------------------------------------

    if diet.lower() == "vegetarian":

        non_veg_words = [
            "chicken",
            "mutton",
            "beef",
            "pork",
            "fish",
            "meat",
            "shrimp",
            "prawn",
        ]

        for word in non_veg_words:

            if word in recipe_text:
                return False, (
                    f"{recipe_name}: recipe may not satisfy "
                    "the vegetarian preference."
                )

    # -----------------------------------------------------------------------
    # 7. Vegan verification
    # -----------------------------------------------------------------------

    if diet.lower() == "vegan":

        non_vegan_words = [
            "chicken",
            "mutton",
            "beef",
            "pork",
            "fish",
            "meat",
            "shrimp",
            "prawn",
            "egg",
            "milk",
            "cheese",
            "butter",
            "cream",
            "yogurt",
            "curd",
        ]

        for word in non_vegan_words:

            if word in recipe_text:
                return False, (
                    f"{recipe_name}: recipe may not satisfy "
                    "the vegan preference."
                )

    # -----------------------------------------------------------------------
    # 8. Gluten-free verification
    # -----------------------------------------------------------------------

    if diet.lower() == "gluten-free":

        gluten_words = [
            "wheat",
            "maida",
            "flour",
            "bread",
            "pasta",
            "barley",
            "rye",
        ]

        for word in gluten_words:

            if word in recipe_text:
                return False, (
                    f"{recipe_name}: recipe may contain "
                    "gluten-containing ingredients."
                )

    # -----------------------------------------------------------------------
    # 9. Verification successful
    # -----------------------------------------------------------------------

    return True, "Recipe verified successfully."


# ===========================================================================
# CUSTOM CSS
# ===========================================================================

st.markdown(
    """
    <style>

    .sb-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 16px;
        padding: 24px 28px;
        margin-bottom: 20px;
    }

    .sb-hero {
        background: linear-gradient(
            135deg,
            #ecfdf5 0%,
            #f0fdf4 100%
        );
        border: 1px solid #d1fae5;
        border-radius: 16px;
        padding: 28px 32px;
        margin-bottom: 20px;
    }

    .sb-pill-green {
        display: inline-block;
        background: #ecfdf5;
        color: #059669;
        border: 1px solid #a7f3d0;
        border-radius: 20px;
        padding: 6px 16px;
        font-size: 13px;
        font-weight: 600;
        margin: 4px 6px 4px 0;
    }

    .sb-pill-blue {
        display: inline-block;
        background: #eff6ff;
        color: #2563eb;
        border: 1px solid #bfdbfe;
        border-radius: 20px;
        padding: 6px 16px;
        font-size: 13px;
        font-weight: 600;
        margin: 4px 6px 4px 0;
    }

    .sb-pill-gray {
        display: inline-block;
        background: #f9fafb;
        color: #6b7280;
        border: 1px solid #e5e7eb;
        border-radius: 20px;
        padding: 6px 16px;
        font-size: 13px;
        font-weight: 600;
        margin: 4px 6px 4px 0;
    }

    .sb-eyebrow {
        display: inline-block;
        background: #d1fae5;
        color: #047857;
        border-radius: 20px;
        padding: 4px 14px;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.03em;
        margin-bottom: 12px;
    }

    .youtube-card {
        padding: 10px 14px;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        margin-bottom: 8px;
        background: #ffffff;
    }

    .youtube-link {
        text-decoration: none;
        font-weight: 600;
        color: #dc2626;
    }

    .web-card {
        padding: 10px 14px;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        margin-bottom: 8px;
        background: #ffffff;
    }

    .web-link {
        text-decoration: none;
        font-weight: 600;
        color: #2563eb;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ===========================================================================
# SIDEBAR
# ===========================================================================

with st.sidebar:

    st.markdown("### 🥗 SmartBite **AI**")

    st.caption(
        "Recipe & Meal Assistant"
    )

    st.markdown("---")

    page = st.radio(
        "Navigate",
        [
            "🏠 Home",
            "🧭 Discover",
            "📖 My Recipes",
            "🛒 Shopping List",
            "💬 Ask SmartBite AI",
            "ℹ️ About",
        ],
        label_visibility="collapsed",
    )


# ===========================================================================
# HEADER
# ===========================================================================

st.markdown(
    "## 🥗 SmartBite **AI**"
)

st.caption(
    "Turn the ingredients you have into meals you'll love."
)


# ===========================================================================
# HOME PAGE
# ===========================================================================

if page == "🏠 Home":

    st.markdown(
        '<div class="sb-hero">',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<span class="sb-eyebrow">'
        '⚡ INSTANT AI KITCHEN ASSISTANT'
        '</span>',
        unsafe_allow_html=True,
    )

    st.markdown(
        "### What can you cook today?"
    )

    st.write(
        "Tell us what's in your kitchen and SmartBite AI "
        "will match delicious possibilities, clearly showing "
        "what you have and the exact minimal items you need."
    )

    # -----------------------------------------------------------------------
    # RECIPE INPUT FORM
    # -----------------------------------------------------------------------

    with st.form("recipe_form"):

        ingredients = st.text_area(
            "Available ingredients (comma-separated)",
            placeholder=(
                "e.g. rice, onion, tomato, eggs"
            ),
        )

        col1, col2 = st.columns(2)

        with col1:

            cuisine = st.selectbox(
                "Cuisine preference",
                [
                    "Any",
                    "Indian",
                    "Italian",
                    "Chinese",
                    "Mexican",
                    "Continental",
                    "Korean",
                ],
            )

            servings = st.number_input(
                "Servings",
                min_value=1,
                max_value=10,
                value=2,
            )

        with col2:

            time_minutes = st.slider(
                "Cooking time available (minutes)",
                10,
                120,
                30,
            )

            diet = st.selectbox(
                "Dietary preference",
                [
                    "None",
                    "Vegetarian",
                    "Vegan",
                    "Gluten-free",
                ],
            )

        use_web_search = st.checkbox(
            "Also search the web for extra recipe ideas (Tavily)",
            value=True,
        )

        submitted = st.form_submit_button(
            "Get Recipe"
        )

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )


    # =======================================================================
    # PROCESS REQUEST
    # =======================================================================

    if submitted:

        if not ingredients.strip():

            st.error(
                "Please enter at least one ingredient."
            )

        else:

            # ===============================================================
            # NODE 1 — GEMINI
            # ===============================================================

            with st.spinner(
                "🧠 Creating your recipes..."
            ):

                try:

                    result = generate_recipe(
                        ingredients,
                        cuisine,
                        time_minutes,
                        servings,
                        diet,
                    )

                except Exception as e:

                    st.error(
                        f"Something went wrong calling Gemini: {e}"
                    )

                    result = None


            if result:

                raw_recipes = result.get(
                    "recipes",
                    []
                )

                note = result.get(
                    "note",
                    ""
                )


                # ===========================================================
                # NODE 2 — VERIFY NODE
                # ===========================================================

                verified_recipes = []

                rejected_recipes = []


                for recipe in raw_recipes:

                    is_valid, message = verify_recipe(
                        recipe,
                        time_minutes,
                        diet,
                    )

                    if is_valid:

                        verified_recipes.append(
                            recipe
                        )

                    else:

                        rejected_recipes.append(
                            {
                                "recipe": recipe,
                                "reason": message,
                            }
                        )


                recipes = verified_recipes


                # -----------------------------------------------------------
                # Verification result
                # -----------------------------------------------------------

                if recipes:

                    st.success(
                        f"✅ {len(recipes)} recipe(s) "
                        "verified successfully."
                    )

                elif raw_recipes:

                    st.error(
                        "❌ The generated recipes did not "
                        "pass verification."
                    )


                if note:

                    st.info(note)


                # ===========================================================
                # VERIFIED RECIPES
                # ===========================================================

                if not recipes:

                    st.warning(
                        "No suitable verified recipe could "
                        "be generated. Try adding more ingredients "
                        "or increasing the cooking time."
                    )

                else:

                    for recipe in recipes:

                        st.markdown(
                            '<div class="sb-card">',
                            unsafe_allow_html=True,
                        )


                        recipe_name = recipe.get(
                            "recipe_name",
                            "Recipe",
                        )


                        estimated_time = recipe.get(
                            "estimated_time_minutes",
                            "?",
                        )


                        # ---------------------------------------------------
                        # RECIPE NAME
                        # ---------------------------------------------------

                        st.markdown(
                            f"#### 🍽️ {recipe_name} — "
                            f"~{estimated_time} min"
                        )


                        # ---------------------------------------------------
                        # INGREDIENTS USED
                        # ---------------------------------------------------

                        used = recipe.get(
                            "ingredients_used",
                            [],
                        )


                        st.markdown(
                            "**Uses:** "
                            + (
                                ", ".join(used)
                                if used
                                else "—"
                            )
                        )


                        # ---------------------------------------------------
                        # MISSING INGREDIENTS
                        # ---------------------------------------------------

                        missing = recipe.get(
                            "missing_ingredients",
                            [],
                        )


                        if missing:

                            st.markdown(
                                "**Missing "
                                "(you'll need to get these):**"
                            )


                            for item in missing:

                                st.checkbox(
                                    item,
                                    key=(
                                        f"{recipe_name}_{item}"
                                    ),
                                )


                        # ---------------------------------------------------
                        # STEPS
                        # ---------------------------------------------------

                        st.markdown(
                            "**Steps:**"
                        )


                        for i, step in enumerate(
                            recipe.get(
                                "steps",
                                [],
                            ),
                            start=1,
                        ):

                            st.markdown(
                                f"{i}. {step}"
                            )


                        # ===================================================
                        # NODE 3 — YOUTUBE
                        # ===================================================

                        st.markdown(
                            "**📺 Watch on YouTube:**"
                        )


                        try:

                            yt_videos = search_youtube_videos(
                                recipe_name
                            )


                            if yt_videos:

                                for video in yt_videos:

                                    title = video.get(
                                        "title",
                                        "Watch recipe tutorial",
                                    )

                                    url = video.get(
                                        "url",
                                        "",
                                    )


                                    if not url:

                                        continue


                                    st.markdown(
                                        f"""
                                        <div class="youtube-card">
                                            ▶️
                                            <a href="{url}"
                                               target="_blank"
                                               class="youtube-link">
                                                {title}
                                            </a>
                                        </div>
                                        """,
                                        unsafe_allow_html=True,
                                    )


                            else:

                                st.info(
                                    "No YouTube tutorials found."
                                )


                        except Exception as e:

                            st.warning(
                                f"YouTube search failed: {e}"
                            )


                        st.markdown(
                            "</div>",
                            unsafe_allow_html=True,
                        )


                    # =======================================================
                    # SHOPPING LIST
                    # =======================================================

                    shopping_list = build_shopping_list(
                        recipes
                    )


                    if shopping_list:

                        st.markdown(
                            '<div class="sb-card">',
                            unsafe_allow_html=True,
                        )


                        st.markdown(
                            "#### 🛒 Combined Shopping List"
                        )


                        for item in shopping_list:

                            st.write(
                                f"- {item}"
                            )


                        st.markdown(
                            "</div>",
                            unsafe_allow_html=True,
                        )


                # ===========================================================
                # NODE 4 — TAVILY
                # ===========================================================

                if use_web_search:

                    st.markdown(
                        '<div class="sb-card">',
                        unsafe_allow_html=True,
                    )


                    st.markdown(
                        "#### 🔗 More recipe ideas from the web"
                    )


                    st.caption(
                        "Powered by Tavily real-time web search"
                    )


                    if not TAVILY_READY:

                        st.warning(
                            "Tavily API key isn't set in your "
                            ".env file. Add TAVILY_API_KEY "
                            "and restart the app."
                        )


                    else:

                        try:

                            with st.spinner(
                                "🌐 Finding recipes on the web..."
                            ):

                                links = search_recipes(
                                    cuisine,
                                    ingredients,
                                )


                            if links:

                                for link in links:

                                    title = link.get(
                                        "title",
                                        "Recipe website",
                                    )

                                    url = link.get(
                                        "url",
                                        "",
                                    )


                                    if not url:

                                        continue


                                    st.markdown(
                                        f"""
                                        <div class="web-card">
                                            🔗
                                            <a href="{url}"
                                               target="_blank"
                                               class="web-link">
                                                {title}
                                            </a>
                                        </div>
                                        """,
                                        unsafe_allow_html=True,
                                    )


                            else:

                                st.write(
                                    "No web results found "
                                    "for this search."
                                )


                        except Exception as e:

                            st.error(
                                f"Tavily search failed: {e}"
                            )


                    st.markdown(
                        "</div>",
                        unsafe_allow_html=True,
                    )


# ===========================================================================
# DISCOVER PAGE
# ===========================================================================

elif page == "🧭 Discover":

    st.markdown(
        "## 🔥 Popular Recipes"
    )

    st.caption(
        "Find recipes based on the ingredients you have."
    )


    discover_ingredients = st.text_input(
        "Have some ingredients? Type them to see your match % (optional)",
        placeholder="e.g. rice, egg, onion",
        key="discover_ingredients",
    )


    user_ings = (
        _parse_user_ingredients(
            discover_ingredients
        )
        if discover_ingredients.strip()
        else []
    )


    scored_recipes = []


    for recipe in LOCAL_RECIPES:

        if user_ings:

            score, matched, missing = _score_recipe(
                user_ings,
                recipe,
            )

        else:

            score = 0.0
            matched = []
            missing = recipe.get(
                "ingredients",
                [],
            )


        scored_recipes.append(
            (
                score,
                recipe,
                matched,
                missing,
            )
        )


    scored_recipes.sort(
        key=lambda x: x[0],
        reverse=True,
    )


    if "favorites" not in st.session_state:

        st.session_state.favorites = set()


    cols_per_row = 3


    for i in range(
        0,
        len(scored_recipes),
        cols_per_row,
    ):

        row = scored_recipes[
            i:i + cols_per_row
        ]

        cols = st.columns(
            cols_per_row
        )


        for col, (
            score,
            recipe,
            matched,
            missing,
        ) in zip(cols, row):

            with col:

                st.markdown(
                    '<div class="sb-card" '
                    'style="padding:0;overflow:hidden;">',
                    unsafe_allow_html=True,
                )


                img_url = recipe.get(
                    "image_url",
                    "",
                )


                if img_url:

                    st.image(
                        img_url,
                        use_container_width=True,
                    )


                st.markdown(
                    f"**{recipe.get('name', 'Recipe')}**"
                )


                st.markdown(
                    f"""
                    <span class="sb-pill-blue"
                          style="padding:2px 8px;font-size:11px;">
                        🌍 {recipe.get("cuisine", "—")}
                    </span>

                    <span class="sb-pill-gray"
                          style="padding:2px 8px;font-size:11px;">
                        👥 {recipe.get("servings", "?")} serv
                    </span>

                    <span class="sb-pill-gray"
                          style="padding:2px 8px;font-size:11px;">
                        ⚡ {recipe.get("difficulty", "—")}
                    </span>
                    """,
                    unsafe_allow_html=True,
                )


                desc = recipe.get(
                    "description",
                    "",
                )


                st.caption(
                    desc[:90]
                    + (
                        "..."
                        if len(desc) > 90
                        else ""
                    )
                )


                total_ings = len(
                    recipe.get(
                        "ingredients",
                        [],
                    )
                )


                have = len(matched)
                need = len(missing)


                st.markdown(
                    f"""
                    <span style="color:#059669;
                                 font-size:12px;
                                 font-weight:600;">
                        ✓ You have {have}/{total_ings} ingredients
                    </span>

                    &nbsp;&nbsp;

                    <span style="color:#b45309;
                                 font-size:12px;
                                 font-weight:600;">
                        ⚠ {need} missing
                    </span>
                    """,
                    unsafe_allow_html=True,
                )


                btn_col1, btn_col2 = st.columns(
                    [4, 1]
                )


                with btn_col1:

                    view_clicked = st.button(
                        "View Recipe →",
                        key=f"view_{recipe['id']}",
                        use_container_width=True,
                    )


                with btn_col2:

                    is_fav = (
                        recipe["id"]
                        in st.session_state.favorites
                    )


                    if st.button(
                        "♥" if is_fav else "♡",
                        key=f"fav_{recipe['id']}",
                        use_container_width=True,
                    ):

                        if is_fav:

                            st.session_state.favorites.discard(
                                recipe["id"]
                            )

                        else:

                            st.session_state.favorites.add(
                                recipe["id"]
                            )


                        st.rerun()


                # -----------------------------------------------------------
                # FULL RECIPE
                # -----------------------------------------------------------

                if view_clicked:

                    with st.expander(
                        "Full recipe",
                        expanded=True,
                    ):

                        st.markdown(
                            "**Ingredients:** "
                            + ", ".join(
                                recipe.get(
                                    "ingredients",
                                    [],
                                )
                            )
                        )


                        st.markdown(
                            "**Steps:**"
                        )


                        for j, step in enumerate(
                            recipe.get(
                                "steps",
                                [],
                            ),
                            start=1,
                        ):

                            st.markdown(
                                f"{j}. {step}"
                            )


                        tips = recipe.get(
                            "tips"
                        )


                        if tips:

                            st.markdown(
                                f"**Tip:** {tips}"
                            )


                        # ---------------------------------------------------
                        # YOUTUBE
                        # ---------------------------------------------------

                        st.markdown(
                            "**📺 Watch on YouTube:**"
                        )


                        try:

                            yt_videos = search_youtube_videos(
                                recipe.get(
                                    "name",
                                    "",
                                )
                            )


                            if yt_videos:

                                for video in yt_videos:

                                    title = video.get(
                                        "title",
                                        "Watch recipe tutorial",
                                    )

                                    url = video.get(
                                        "url",
                                        "",
                                    )


                                    if not url:

                                        continue


                                    st.markdown(
                                        f"""
                                        <div class="youtube-card">
                                            ▶️
                                            <a href="{url}"
                                               target="_blank"
                                               class="youtube-link">
                                                {title}
                                            </a>
                                        </div>
                                        """,
                                        unsafe_allow_html=True,
                                    )


                            else:

                                st.info(
                                    "No YouTube tutorials found."
                                )


                        except Exception as e:

                            st.warning(
                                f"YouTube search failed: {e}"
                            )


                st.markdown(
                    "</div>",
                    unsafe_allow_html=True,
                )


# ===========================================================================
# MY RECIPES
# ===========================================================================

elif page == "📖 My Recipes":

    st.markdown(
        '<div class="sb-card">',
        unsafe_allow_html=True,
    )

    st.markdown(
        "### 📖 My Recipes"
    )

    st.write(
        "Recipes you've saved will show up here. "
        "(Coming soon.)"
    )

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )


# ===========================================================================
# SHOPPING LIST
# ===========================================================================

elif page == "🛒 Shopping List":

    st.markdown(
        '<div class="sb-card">',
        unsafe_allow_html=True,
    )

    st.markdown(
        "### 🛒 Shopping List"
    )

    st.write(
        "Your combined shopping list across saved recipes. "
        "(Coming soon.)"
    )

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )


# ===========================================================================
# ASK SMARTBITE AI
# ===========================================================================

elif page == "💬 Ask SmartBite AI":

    st.markdown(
        '<div class="sb-card">',
        unsafe_allow_html=True,
    )

    st.markdown(
        "### 💬 Ask SmartBite AI"
    )

    st.write(
        "Free-form chat with the AI about cooking. "
        "(Coming soon.)"
    )

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )


# ===========================================================================
# ABOUT
# ===========================================================================

elif page == "ℹ️ About":

    st.markdown(
        '<div class="sb-card">',
        unsafe_allow_html=True,
    )

    st.markdown(
        "### ℹ️ About SmartBite AI"
    )

    st.write(
        "SmartBite AI turns the ingredients you have into "
        "meal ideas using a local recipe dataset, Gemini "
        "for AI-generated suggestions, and Tavily for "
        "real-time web recipe discovery."
    )


    st.markdown(
        "### 🔄 How SmartBite AI Works"
    )


    st.markdown(
        """
        **User Input**
        
        ↓
        
        **Ingredient & Preference Analysis**
        
        ↓
        
        **Local Recipe Data + Gemini AI**
        
        ↓
        
        **🔍 Verify Node**
        
        ↓
        
        **Verified Recipes**
        
        ↓
        
        **Tavily Real-Time Web Search**
        
        ↓
        
        **YouTube Cooking Tutorials**
        
        ↓
        
        **Shopping List**
        
        ↓
        
        **Streamlit User Interface**
        """
    )


    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )
