import os
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

# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

GEMINI_READY = bool(GEMINI_API_KEY)
TAVILY_READY = bool(TAVILY_API_KEY)

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="SmartBite AI",
    page_icon="🥗",
    layout="wide"
)

# ============================================================
# STYLING
# ============================================================

st.markdown("""
<style>

.sb-card {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 16px;
    padding: 24px 28px;
    margin-bottom: 20px;
}

.sb-hero {
    background: linear-gradient(135deg, #ecfdf5 0%, #f0fdf4 100%);
    border: 1px solid #d1fae5;
    border-radius: 16px;
    padding: 28px 32px;
    margin-bottom: 20px;
}

.sb-badge {
    display: inline-block;
    background: #f3f4f6;
    color: #374151;
    border-radius: 20px;
    padding: 4px 14px;
    font-size: 13px;
    font-weight: 600;
    margin-right: 6px;
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
    padding: 12px 16px;
    border: 1px solid #fecaca;
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
}

.web-link {
    text-decoration: none;
    font-weight: 600;
    color: #2563eb;
}

</style>
""", unsafe_allow_html=True)

# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown("### 🥗 SmartBite **AI**")
    st.caption("Recipe & Meal Assistant")
    st.markdown("---")

    page = st.radio(
        "Navigate",
        [
            "🏠 Home",
            "🧭 Discover",
            "📖 My Recipes",
            "🛒 Shopping List",
            "💬 Ask SmartBite AI",
            "ℹ️ About"
        ],
        label_visibility="collapsed",
    )

    st.markdown("---")

    st.markdown("**ENGINE STATUS**")

    if GEMINI_READY:
        st.success("🧠 Gemini API Ready")
    else:
        st.warning("🧠 Gemini API Not Configured")

    if TAVILY_READY:
        st.success("🌐 Tavily API Ready")
    else:
        st.warning("🌐 Tavily API Not Configured")

# ============================================================
# HEADER
# ============================================================

header_col1, header_col2 = st.columns([5, 1])

with header_col1:
    st.markdown("## 🥗 SmartBite **AI**")
    st.caption("Turn the ingredients you have into meals you'll love.")

with header_col2:
    st.markdown(
        '<span class="sb-badge">🎓 Student & Beginner Edition</span>',
        unsafe_allow_html=True
    )

# ============================================================
# FUNCTION: SHOW YOUTUBE LINKS
# ============================================================

def show_youtube_videos(recipe_name):

    st.markdown("### 📺 YouTube Cooking Tutorials")

    if not recipe_name:
        st.info("Recipe name is missing.")
        return

    try:

        with st.spinner("Finding YouTube tutorials..."):

            yt_videos = search_youtube_videos(recipe_name)

        if yt_videos:

            for video in yt_videos:

                title = video.get(
                    "title",
                    "Watch recipe tutorial"
                )

                url = video.get("url", "")

                if not url:
                    continue

                st.markdown(
                    f"""
                    <div class="youtube-card">

                        ▶️
                        <a
                            href="{url}"
                            target="_blank"
                            class="youtube-link"
                        >
                            {title}
                        </a>

                    </div>
                    """,
                    unsafe_allow_html=True
                )

        else:

            st.info(
                f"No YouTube tutorials found for '{recipe_name}'."
            )

    except Exception as e:

        st.warning(
            f"Could not load YouTube tutorials: {e}"
        )

# ============================================================
# HOME PAGE
# ============================================================

if page == "🏠 Home":

    st.markdown(
        '<div class="sb-hero">',
        unsafe_allow_html=True
    )

    st.markdown(
        '<span class="sb-eyebrow">'
        '⚡ INSTANT AI KITCHEN ASSISTANT'
        '</span>',
        unsafe_allow_html=True
    )

    st.markdown("### What can you cook today?")

    st.write(
        "Tell us what's in your kitchen and SmartBite AI "
        "will match delicious possibilities, clearly showing "
        "what you have and the exact minimal items you need."
    )

    # --------------------------------------------------------
    # RECIPE FORM
    # --------------------------------------------------------

    with st.form("recipe_form"):

        ingredients = st.text_area(
            "Available ingredients (comma-separated)",
            placeholder="e.g. rice, onion, tomato, eggs"
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
                    "Korean"
                ]
            )

            servings = st.number_input(
                "Servings",
                min_value=1,
                max_value=10,
                value=2
            )

        with col2:

            time_minutes = st.slider(
                "Cooking time available (minutes)",
                10,
                120,
                30
            )

            diet = st.selectbox(
                "Dietary preference",
                [
                    "None",
                    "Vegetarian",
                    "Vegan",
                    "Gluten-free"
                ]
            )

        use_web_search = st.checkbox(
            "Also search the web for extra recipe ideas (Tavily)",
            value=False
        )

        submitted = st.form_submit_button(
            "🍳 Get Recipe",
            use_container_width=True
        )

    st.markdown(
        '</div>',
        unsafe_allow_html=True
    )

    # ========================================================
    # WHEN GET RECIPE IS CLICKED
    # ========================================================

    if submitted:

        if not ingredients.strip():

            st.error(
                "Please enter at least one ingredient."
            )

        else:

            # ------------------------------------------------
            # GEMINI
            # ------------------------------------------------

            with st.spinner(
                "🧠 Gemini is creating your recipes..."
            ):

                try:

                    result = generate_recipe(
                        ingredients,
                        cuisine,
                        time_minutes,
                        servings,
                        diet
                    )

                except Exception as e:

                    st.error(
                        f"Something went wrong calling Gemini: {e}"
                    )

                    result = None

            # ------------------------------------------------
            # RESULT
            # ------------------------------------------------

            if result:

                recipes = result.get(
                    "recipes",
                    []
                )

                note = result.get(
                    "note",
                    ""
                )

                if recipes:

                    st.balloons()

                if note:

                    st.info(note)

                # ------------------------------------------------
                # NO RECIPES
                # ------------------------------------------------

                if not recipes:

                    st.warning(
                        "No suitable recipe could be generated. "
                        "Try adding a few more ingredients."
                    )

                # ------------------------------------------------
                # RECIPES
                # ------------------------------------------------

                else:

                    for recipe_index, recipe in enumerate(recipes):

                        recipe_name = recipe.get(
                            "recipe_name",
                            "Recipe"
                        )

                        st.markdown(
                            '<div class="sb-card">',
                            unsafe_allow_html=True
                        )

                        # ----------------------------------------
                        # TITLE
                        # ----------------------------------------

                        st.markdown(
                            f"#### 🍽️ {recipe_name} — "
                            f"~{recipe.get('estimated_time_minutes', '?')} min"
                        )

                        # ----------------------------------------
                        # INGREDIENTS USED
                        # ----------------------------------------

                        used = recipe.get(
                            "ingredients_used",
                            []
                        )

                        st.markdown(
                            "**Uses:** " +
                            (
                                ", ".join(used)
                                if used
                                else "—"
                            )
                        )

                        # ----------------------------------------
                        # MISSING INGREDIENTS
                        # ----------------------------------------

                        missing = recipe.get(
                            "missing_ingredients",
                            []
                        )

                        if missing:

                            st.markdown(
                                "**Missing ingredients:**"
                            )

                            for item_index, item in enumerate(missing):

                                st.checkbox(
                                    item,
                                    key=(
                                        f"missing_"
                                        f"{recipe_index}_"
                                        f"{item_index}"
                                    )
                                )

                        # ----------------------------------------
                        # STEPS
                        # ----------------------------------------

                        st.markdown("**Steps:**")

                        steps = recipe.get(
                            "steps",
                            []
                        )

                        for i, step in enumerate(
                            steps,
                            start=1
                        ):

                            st.markdown(
                                f"**{i}.** {step}"
                            )

                        # =================================================
                        # YOUTUBE LINKS
                        # =================================================

                        show_youtube_videos(
                            recipe_name
                        )

                        st.markdown(
                            '</div>',
                            unsafe_allow_html=True
                        )

                    # ------------------------------------------------
                    # SHOPPING LIST
                    # ------------------------------------------------

                    shopping_list = build_shopping_list(
                        recipes
                    )

                    if shopping_list:

                        st.markdown(
                            '<div class="sb-card">',
                            unsafe_allow_html=True
                        )

                        st.markdown(
                            "#### 🛒 Combined Shopping List"
                        )

                        for item in shopping_list:

                            st.write(
                                f"- {item}"
                            )

                        st.markdown(
                            '</div>',
                            unsafe_allow_html=True
                        )

                # =================================================
                # TAVILY WEB SEARCH
                # =================================================

                if use_web_search:

                    st.markdown(
                        '<div class="sb-card">',
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        "#### 🔗 More Recipe Ideas From The Web"
                    )

                    st.caption(
                        "Powered by Tavily real-time web search"
                    )

                    if not TAVILY_READY:

                        st.warning(
                            "Tavily API key isn't set. "
                            "Add TAVILY_API_KEY to your .env file."
                        )

                    else:

                        try:

                            with st.spinner(
                                "🌐 Searching the web with Tavily..."
                            ):

                                links = search_recipes(
                                    cuisine,
                                    ingredients
                                )

                            if links:

                                for link in links:

                                    title = link.get(
                                        "title",
                                        "Recipe"
                                    )

                                    url = link.get(
                                        "url",
                                        ""
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
                                            unsafe_allow_html=True
                                        )

                            else:

                                st.info(
                                    "No web results found."
                                )

                        except Exception as e:

                            st.error(
                                f"Tavily search failed: {e}"
                            )

                    st.markdown(
                        '</div>',
                        unsafe_allow_html=True
                    )

    # ========================================================
    # ENGINE ARCHITECTURE
    # ========================================================

    st.markdown(
        '<div class="sb-card">',
        unsafe_allow_html=True
    )

    st.markdown(
        "**ENGINE ARCHITECTURE:**"
    )

    gemini_status = (
        "Ready"
        if GEMINI_READY
        else "Add Key"
    )

    tavily_status = (
        "Ready"
        if TAVILY_READY
        else "Add Key"
    )

    st.markdown(
        f"""
        <span class="sb-pill-blue">
            🧠 Gemini — AI Reasoning & Personalization
            (⚡ {gemini_status})
        </span>

        <span class="sb-pill-green">
            🌐 Tavily — Real-Time Web & Recipe Search
            (⚡ {tavily_status})
        </span>

        <span class="sb-pill-gray">
            📺 YouTube — Cooking Tutorials
        </span>

        <span class="sb-pill-gray">
            📦 Local Dataset — 25 Recipes & Offline Fallback
        </span>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        '</div>',
        unsafe_allow_html=True
    )

# ============================================================
# DISCOVER PAGE
# ============================================================

elif page == "🧭 Discover":

    st.markdown("## 🔥 Popular with Students")

    st.caption(
        "Curated student favorites that never fail."
    )

    discover_ingredients = st.text_input(
        "Have some ingredients? "
        "Type them to see your match % (optional)",
        placeholder="e.g. rice, egg, onion",
        key="discover_ingredients"
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
                recipe
            )

        else:

            score = 0.0
            matched = []
            missing = recipe.get(
                "ingredients",
                []
            )

        scored_recipes.append(
            (
                score,
                recipe,
                matched,
                missing
            )
        )

    scored_recipes.sort(
        key=lambda x: x[0],
        reverse=True
    )

    if "favorites" not in st.session_state:

        st.session_state.favorites = set()

    cols_per_row = 3

    for i in range(
        0,
        len(scored_recipes),
        cols_per_row
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
            missing
        ) in zip(cols, row):

            with col:

                st.markdown(
                    '<div class="sb-card" '
                    'style="padding:0;overflow:hidden;">',
                    unsafe_allow_html=True
                )

                # IMAGE

                img_url = recipe.get(
                    "image_url",
                    ""
                )

                if img_url:

                    st.image(
                        img_url,
                        use_container_width=True
                    )

                # MATCH

                st.markdown(
                    f"""
                    <div style="padding:14px 16px 4px 16px;">

                        <span class="sb-pill-green"
                              style="padding:3px 10px;font-size:12px;">

                            ⭐ {int(score * 100)}% match

                        </span>

                        <span class="sb-pill-gray"
                              style="padding:3px 10px;font-size:12px;">

                            ⏱ {recipe.get("cooking_time", "?")} min

                        </span>

                    </div>
                    """,
                    unsafe_allow_html=True
                )

                # NAME

                recipe_name = recipe.get(
                    "name",
                    "Recipe"
                )

                st.markdown(
                    f"**{recipe_name}**"
                )

                # INFO

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
                    unsafe_allow_html=True
                )

                # DESCRIPTION

                desc = recipe.get(
                    "description",
                    ""
                )

                st.caption(
                    desc[:90] +
                    ("..." if len(desc) > 90 else "")
                )

                # INGREDIENT COUNT

                total_ings = len(
                    recipe.get(
                        "ingredients",
                        []
                    )
                )

                have = len(matched)
                need = len(missing)

                st.markdown(
                    f"""
                    <span style="
                        color:#059669;
                        font-size:12px;
                        font-weight:600;
                    ">

                        ✓ You have {have}/{total_ings}
                        ingredients

                    </span>

                    &nbsp;&nbsp;

                    <span style="
                        color:#b45309;
                        font-size:12px;
                        font-weight:600;
                    ">

                        ⚠ {need} missing

                    </span>
                    """,
                    unsafe_allow_html=True
                )

                # BUTTONS

                btn_col1, btn_col2 = st.columns(
                    [4, 1]
                )

                with btn_col1:

                    view_clicked = st.button(
                        "View Recipe →",
                        key=f"view_{recipe['id']}",
                        use_container_width=True
                    )

                with btn_col2:

                    is_fav = (
                        recipe["id"]
                        in st.session_state.favorites
                    )

                    if st.button(
                        "♥" if is_fav else "♡",
                        key=f"fav_{recipe['id']}",
                        use_container_width=True
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

                # =================================================
                # FULL RECIPE
                # =================================================

                if view_clicked:

                    with st.expander(
                        "Full recipe",
                        expanded=True
                    ):

                        st.markdown(
                            "**Ingredients:** " +
                            ", ".join(
                                recipe.get(
                                    "ingredients",
                                    []
                                )
                            )
                        )

                        st.markdown(
                            "**Steps:**"
                        )

                        for j, step in enumerate(
                            recipe.get(
                                "steps",
                                []
                            ),
                            start=1
                        ):

                            st.markdown(
                                f"**{j}.** {step}"
                            )

                        tips = recipe.get(
                            "tips"
                        )

                        if tips:

                            st.markdown(
                                f"**Tip:** {tips}"
                            )

                        # -----------------------------------------
                        # YOUTUBE
                        # -----------------------------------------

                        show_youtube_videos(
                            recipe_name
                        )

                st.markdown(
                    '</div>',
                    unsafe_allow_html=True
                )

# ============================================================
# MY RECIPES
# ============================================================

elif page == "📖 My Recipes":

    st.markdown(
        '<div class="sb-card">',
        unsafe_allow_html=True
    )

    st.markdown(
        "### 📖 My Recipes"
    )

    st.write(
        "Recipes you've saved will show up here. "
        "(Coming soon.)"
    )

    st.markdown(
        '</div>',
        unsafe_allow_html=True
    )

# ============================================================
# SHOPPING LIST
# ============================================================

elif page == "🛒 Shopping List":

    st.markdown(
        '<div class="sb-card">',
        unsafe_allow_html=True
    )

    st.markdown(
        "### 🛒 Shopping List"
    )

    st.write(
        "Your combined shopping list across saved recipes. "
        "(Coming soon.)"
    )

    st.markdown(
        '</div>',
        unsafe_allow_html=True
    )

# ============================================================
# ASK SMARTBITE AI
# ============================================================

elif page == "💬 Ask SmartBite AI":

    st.markdown(
        '<div class="sb-card">',
        unsafe_allow_html=True
    )

    st.markdown(
        "### 💬 Ask SmartBite AI"
    )

    st.write(
        "Free-form chat with the AI about cooking. "
        "(Coming soon.)"
    )

    st.markdown(
        '</div>',
        unsafe_allow_html=True
    )

# ============================================================
# ABOUT
# ============================================================

elif page == "ℹ️ About":

    st.markdown(
        '<div class="sb-card">',
        unsafe_allow_html=True
    )

    st.markdown(
        "### ℹ️ About SmartBite AI"
    )

    st.write(
        "SmartBite AI turns the ingredients you have "
        "into meal ideas using:"
    )

    st.markdown("""
    - 🧠 **Gemini API** — AI recipe generation
    - 🌐 **Tavily API** — real-time web recipe search
    - 📺 **YouTube search** — cooking tutorials
    - 📦 **Local recipe dataset** — offline fallback
    """)

    st.markdown(
        '</div>',
        unsafe_allow_html=True
    )
