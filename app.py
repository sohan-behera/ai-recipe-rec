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

# ============================================================================
# LOAD ENVIRONMENT
# ============================================================================

load_dotenv()

GEMINI_READY = bool(GEMINI_API_KEY)
TAVILY_READY = bool(TAVILY_API_KEY)


# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="SmartBite AI",
    page_icon="🥗",
    layout="wide",
)


# ============================================================================
# VERIFY NODE
# ============================================================================

def verify_recipe(recipe, time_minutes, diet):

    if not isinstance(recipe, dict):
        return False, "Recipe is not in the correct format."

    recipe_name = str(
        recipe.get("recipe_name", "")
    ).strip()

    if not recipe_name:
        return False, "Recipe name is missing."

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

    # ------------------------------------------------------------------------
    # Vegetarian
    # ------------------------------------------------------------------------

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
                    f"{recipe_name}: recipe may not "
                    "satisfy the vegetarian preference."
                )

    # ------------------------------------------------------------------------
    # Vegan
    # ------------------------------------------------------------------------

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
                    f"{recipe_name}: recipe may not "
                    "satisfy the vegan preference."
                )

    # ------------------------------------------------------------------------
    # Gluten Free
    # ------------------------------------------------------------------------

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

    return True, "Recipe verified successfully."


# ============================================================================
# CUSTOM CSS
# ============================================================================

st.markdown(
    """
    <style>

    .sb-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 16px;
        padding: 22px;
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

    .sb-eyebrow {
        display: inline-block;

        background: #d1fae5;
        color: #047857;

        border-radius: 20px;

        padding: 5px 14px;

        font-size: 12px;
        font-weight: 700;

        margin-bottom: 10px;
    }

    /* ================================================================
       YOUTUBE LINK CARD
       ================================================================ */

    .youtube-card {
        padding: 12px 15px;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        margin-bottom: 10px;
        background: white;
    }

    .youtube-link {
        text-decoration: none;
        font-weight: 600;
        color: #dc2626;
        font-size: 15px;
    }

    .youtube-link:hover {
        text-decoration: underline;
        color: #b91c1c;
    }

    /* ================================================================
       WEB LINK CARD
       ================================================================ */

    .web-card {
        padding: 12px 15px;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        margin-bottom: 10px;
        background: white;
    }

    .web-link {
        text-decoration: none;
        font-weight: 600;
        color: #2563eb;
        font-size: 15px;
    }

    .web-link:hover {
        text-decoration: underline;
        color: #1d4ed8;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:

    st.markdown(
        "### 🥗 SmartBite **AI**"
    )

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


# ============================================================================
# HEADER
# ============================================================================

st.markdown(
    "## 🥗 SmartBite **AI**"
)

st.caption(
    "Turn the ingredients you have into meals you'll love."
)


# ============================================================================
# HOME
# ============================================================================

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
        "Tell us what's in your kitchen and "
        "SmartBite AI will create suitable meals."
    )

    # ------------------------------------------------------------------------
    # INPUT FORM
    # ------------------------------------------------------------------------

    with st.form("recipe_form"):

        ingredients = st.text_area(
            "Available ingredients",
            placeholder=(
                "e.g. rice, onion, tomato, egg"
            ),
        )

        col1, col2 = st.columns(2)

        with col1:

            cuisine = st.selectbox(
                "Cuisine",
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
                "Available cooking time",
                10,
                120,
                30,
            )

            diet = st.selectbox(
                "Diet",
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
            "🍳 Get Recipe",
            use_container_width=True,
        )

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )


    # ------------------------------------------------------------------------
    # GENERATE RECIPE
    # ------------------------------------------------------------------------

    if submitted:

        if not ingredients.strip():

            st.error(
                "Please enter at least one ingredient."
            )

        else:

            with st.spinner(
                "🧠 Creating recipes..."
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
                        f"Gemini error: {e}"
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

                # ============================================================
                # VERIFY NODE
                # ============================================================

                verified_recipes = []

                rejected_recipes = []

                for recipe in raw_recipes:

                    valid, message = verify_recipe(
                        recipe,
                        time_minutes,
                        diet,
                    )

                    if valid:

                        verified_recipes.append(
                            recipe
                        )

                    else:

                        rejected_recipes.append(
                            message
                        )

                recipes = verified_recipes


                if note:

                    st.info(note)


                if recipes:

                    st.success(
                        f"✅ {len(recipes)} recipe(s) "
                        "verified successfully."
                    )

                else:

                    st.warning(
                        "No suitable verified recipe was found."
                    )


                # ============================================================
                # DISPLAY VERIFIED RECIPES
                # ============================================================

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

                    st.markdown(
                        f"### 🍽️ {recipe_name}"
                    )

                    st.caption(
                        f"⏱ Approximately {estimated_time} minutes"
                    )

                    # --------------------------------------------------------
                    # USED INGREDIENTS
                    # --------------------------------------------------------

                    st.markdown(
                        "**Ingredients used**"
                    )

                    for item in recipe.get(
                        "ingredients_used",
                        [],
                    ):

                        st.write(
                            f"• {item}"
                        )

                    # --------------------------------------------------------
                    # MISSING INGREDIENTS
                    # --------------------------------------------------------

                    missing = recipe.get(
                        "missing_ingredients",
                        [],
                    )

                    if missing:

                        st.markdown(
                            "**🛒 Missing ingredients**"
                        )

                        for item in missing:

                            st.checkbox(
                                item,
                                key=f"{recipe_name}_{item}",
                            )

                    # --------------------------------------------------------
                    # STEPS
                    # --------------------------------------------------------

                    st.markdown(
                        "**👨‍🍳 Cooking steps**"
                    )

                    for number, step in enumerate(
                        recipe.get(
                            "steps",
                            [],
                        ),
                        start=1,
                    ):

                        st.markdown(
                            f"**{number}.** {step}"
                        )

                    # --------------------------------------------------------
                    # YOUTUBE
                    # --------------------------------------------------------

                    st.markdown(
                        "**📺 Cooking tutorials**"
                    )

                    try:

                        videos = search_youtube_videos(
                            recipe_name
                        )

                        if videos:

                            for video in videos:

                                title = video.get(
                                    "title",
                                    "Watch tutorial",
                                )

                                url = video.get(
                                    "url",
                                    "",
                                )

                                if url:

                                    # Clickable YouTube title
                                    st.markdown(
                                        f"""
                                        <div class="youtube-card">

                                            <span style="
                                                font-size:18px;
                                                margin-right:6px;
                                            ">
                                                ▶️
                                            </span>

                                            <a
                                                href="{url}"
                                                target="_blank"
                                                class="youtube-link"
                                            >
                                                {title}
                                            </a>

                                            <div style="
                                                font-size:12px;
                                                color:#777;
                                                margin-top:5px;
                                                margin-left:29px;
                                            ">
                                                Watch on YouTube ↗
                                            </div>

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


                # ============================================================
                # SHOPPING LIST
                # ============================================================

                shopping_list = build_shopping_list(
                    recipes
                )

                if shopping_list:

                    st.markdown(
                        '<div class="sb-card">',
                        unsafe_allow_html=True,
                    )

                    st.markdown(
                        "### 🛒 Shopping List"
                    )

                    for item in shopping_list:

                        st.write(
                            f"☐ {item}"
                        )

                    st.markdown(
                        "</div>",
                        unsafe_allow_html=True,
                    )


                # ============================================================
                # TAVILY
                # ============================================================

                if use_web_search:

                    st.markdown(
                        '<div class="sb-card">',
                        unsafe_allow_html=True,
                    )

                    st.markdown(
                        "### 🔗 More Recipes From The Web"
                    )

                    st.caption(
                        "Real-time results powered by Tavily"
                    )

                    if not TAVILY_READY:

                        st.warning(
                            "Tavily API key is missing. "
                            "Add TAVILY_API_KEY to your .env file."
                        )

                    else:

                        try:

                            with st.spinner(
                                "🌐 Searching the web..."
                            ):

                                links = search_recipes(
                                    cuisine,
                                    ingredients,
                                )

                            if links:

                                for link in links:

                                    title = link.get(
                                        "title",
                                        "Recipe",
                                    )

                                    url = link.get(
                                        "url",
                                        "",
                                    )

                                    if url:

                                        st.markdown(
                                            f"""
                                            <div class="web-card">

                                                🔗

                                                <a
                                                    href="{url}"
                                                    target="_blank"
                                                    class="web-link"
                                                >
                                                    {title}
                                                </a>

                                            </div>
                                            """,
                                            unsafe_allow_html=True,
                                        )

                            else:

                                st.info(
                                    "No web recipes found."
                                )

                        except Exception as e:

                            st.error(
                                f"Tavily search failed: {e}"
                            )

                    st.markdown(
                        "</div>",
                        unsafe_allow_html=True,
                    )


# ============================================================================
# DISCOVER
# ============================================================================

elif page == "🧭 Discover":

    st.markdown(
        "## 🔥 Discover Recipes"
    )

    st.caption(
        "Enter your ingredients to find the best matching recipes."
    )

    # ------------------------------------------------------------------------
    # USER INGREDIENTS
    # ------------------------------------------------------------------------

    discover_ingredients = st.text_input(
        "What ingredients do you have?",
        placeholder="e.g. rice, egg, onion, tomato",
        key="discover_ingredients",
    )

    if discover_ingredients.strip():

        user_ings = _parse_user_ingredients(
            discover_ingredients
        )

    else:

        user_ings = []


    # ------------------------------------------------------------------------
    # SCORE RECIPES
    # ------------------------------------------------------------------------

    scored_recipes = []

    for recipe in LOCAL_RECIPES:

        if user_ings:

            score, matched, missing = _score_recipe(
                user_ings,
                recipe,
            )

        else:

            score = 0

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


    # ------------------------------------------------------------------------
    # FAVORITES
    # ------------------------------------------------------------------------

    if "favorites" not in st.session_state:

        st.session_state.favorites = set()


    # ------------------------------------------------------------------------
    # RECIPE CARDS
    # ------------------------------------------------------------------------

    for i in range(
        0,
        len(scored_recipes),
        3,
    ):

        row = scored_recipes[
            i:i + 3
        ]

        columns = st.columns(3)

        for column, (
            score,
            recipe,
            matched,
            missing,
        ) in zip(
            columns,
            row,
        ):

            with column:

                # ==========================================================
                # IMAGE
                # ==========================================================

                image_url = recipe.get(
                    "image_url",
                    "",
                )

                if image_url:

                    st.image(
                        image_url,
                        use_container_width=True,
                    )

                # ==========================================================
                # MATCH + TIME
                # ==========================================================

                badge1, badge2 = st.columns(2)

                with badge1:

                    st.markdown(
                        f"""
                        <div style="
                            display:inline-block;
                            background:#ecfdf5;
                            color:#059669;
                            border:1px solid #a7f3d0;
                            border-radius:20px;
                            padding:4px 10px;
                            font-size:12px;
                            font-weight:600;
                            white-space:nowrap;
                        ">
                            ⭐ {int(score * 100)}% match
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                with badge2:

                    st.markdown(
                        f"""
                        <div style="
                            display:inline-block;
                            background:#f9fafb;
                            color:#6b7280;
                            border:1px solid #e5e7eb;
                            border-radius:20px;
                            padding:4px 10px;
                            font-size:12px;
                            font-weight:600;
                            white-space:nowrap;
                        ">
                            ⏱ {recipe.get("cooking_time", "?")} min
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )


                # ==========================================================
                # NAME
                # ==========================================================

                st.markdown(
                    f"### {recipe.get('name', 'Recipe')}"
                )


                # ==========================================================
                # INFO
                # ==========================================================

                st.markdown(
                    f"🌍 **{recipe.get('cuisine', '—')}**  "
                    f"👥 **{recipe.get('servings', '?')} serv**  "
                    f"⚡ **{recipe.get('difficulty', '—')}**"
                )


                # ==========================================================
                # DESCRIPTION
                # ==========================================================

                description = recipe.get(
                    "description",
                    "",
                )

                if len(description) > 100:

                    description = (
                        description[:100]
                        + "..."
                    )

                st.caption(
                    description
                )


                # ==========================================================
                # INGREDIENT MATCH
                # ==========================================================

                total = len(
                    recipe.get(
                        "ingredients",
                        [],
                    )
                )

                matched_count = len(
                    matched
                )

                missing_count = len(
                    missing
                )


                if user_ings:

                    st.markdown(
                        f"""
                        <div style="
                            font-size:13px;
                            margin:8px 0;
                        ">

                            <span style="
                                color:#059669;
                                font-weight:600;
                            ">
                                ✓ You have {matched_count}/{total} ingredients
                            </span>

                            <br>

                            <span style="
                                color:#b45309;
                                font-weight:600;
                            ">
                                ⚠ {missing_count} missing
                            </span>

                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                else:

                    st.caption(
                        f"{total} ingredients required"
                    )


                # ==========================================================
                # BUTTONS
                # ==========================================================

                button1, button2 = st.columns(
                    [4, 1]
                )


                with button1:

                    view_clicked = st.button(
                        "View Recipe →",
                        key=f"view_{recipe['id']}",
                        use_container_width=True,
                    )


                with button2:

                    is_favorite = (
                        recipe["id"]
                        in st.session_state.favorites
                    )

                    favorite_clicked = st.button(
                        "♥" if is_favorite else "♡",
                        key=f"fav_{recipe['id']}",
                        use_container_width=True,
                    )

                    if favorite_clicked:

                        if is_favorite:

                            st.session_state.favorites.remove(
                                recipe["id"]
                            )

                        else:

                            st.session_state.favorites.add(
                                recipe["id"]
                            )

                        st.rerun()


                # ==========================================================
                # VIEW RECIPE
                # ==========================================================

                if view_clicked:

                    with st.expander(
                        "📖 Recipe Details",
                        expanded=True,
                    ):

                        st.markdown(
                            "### Ingredients"
                        )

                        for ingredient in recipe.get(
                            "ingredients",
                            [],
                        ):

                            st.write(
                                f"• {ingredient}"
                            )


                        st.markdown(
                            "### Cooking Steps"
                        )

                        for number, step in enumerate(
                            recipe.get(
                                "steps",
                                [],
                            ),
                            start=1,
                        ):

                            st.markdown(
                                f"**{number}.** {step}"
                            )


                        tips = recipe.get(
                            "tips",
                            "",
                        )

                        if tips:

                            st.info(
                                f"💡 {tips}"
                            )


                        # --------------------------------------------------
                        # YOUTUBE
                        # --------------------------------------------------

                        st.markdown(
                            "### 📺 Cooking Tutorials"
                        )

                        try:

                            videos = search_youtube_videos(
                                recipe.get(
                                    "name",
                                    "",
                                )
                            )

                            if videos:

                                for video in videos:

                                    title = video.get(
                                        "title",
                                        "Watch tutorial",
                                    )

                                    url = video.get(
                                        "url",
                                        "",
                                    )

                                    if url:

                                        st.markdown(
                                            f"""
                                            <div class="youtube-card">

                                                <span style="
                                                    font-size:18px;
                                                    margin-right:6px;
                                                ">
                                                    ▶️
                                                </span>

                                                <a
                                                    href="{url}"
                                                    target="_blank"
                                                    class="youtube-link"
                                                >
                                                    {title}
                                                </a>

                                                <div style="
                                                    font-size:12px;
                                                    color:#777;
                                                    margin-top:5px;
                                                    margin-left:29px;
                                                ">
                                                    Watch on YouTube ↗
                                                </div>

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

                st.markdown("---")


# ============================================================================
# MY RECIPES
# ============================================================================

elif page == "📖 My Recipes":

    st.markdown(
        "## 📖 My Recipes"
    )

    st.info(
        "Saved recipes will appear here. Coming soon."
    )


# ============================================================================
# SHOPPING LIST
# ============================================================================

elif page == "🛒 Shopping List":

    st.markdown(
        "## 🛒 Shopping List"
    )

    st.info(
        "Your shopping list will appear here. Coming soon."
    )


# ============================================================================
# ASK SMARTBITE AI
# ============================================================================

elif page == "💬 Ask SmartBite AI":

    st.markdown(
        "## 💬 Ask SmartBite AI"
    )

    st.info(
        "AI cooking chat will be available here. Coming soon."
    )


# ============================================================================
# ABOUT
# ============================================================================

elif page == "ℹ️ About":

    st.markdown(
        "## ℹ️ About SmartBite AI"
    )

    st.write(
        """
        SmartBite AI is an AI-powered recipe assistant
        that helps users turn available ingredients into
        useful meal ideas.
        """
    )

    st.markdown(
        "### 🔄 SmartBite AI Workflow"
    )

    st.markdown(
        """
        **1. User Input**

        ↓

        **2. Ingredient + Preference Analysis**

        ↓

        **3. Local Recipe Data + Gemini AI**

        ↓

        **4. 🔍 Verify Node**

        ↓

        **5. Verified Recipes**

        ↓

        **6. Tavily Real-Time Web Search**

        ↓

        **7. YouTube Cooking Tutorials**

        ↓

        **8. Shopping List**

        ↓

        **9. Streamlit User Interface**
        """
    )
