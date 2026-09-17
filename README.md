# AI Recipe & Meal Recommendation Assistant

## Setup in VS Code

1. Open this folder in VS Code (`File > Open Folder`).
2. Open a terminal (`` Ctrl+` ``) and create a virtual environment:
   ```
   python -m venv venv
   ```
3. Activate it:
   - Windows: `venv\Scripts\activate`
   - Mac/Linux: `source venv/bin/activate`
   - In VS Code, also select this venv as your Python interpreter (bottom-right corner or `Ctrl+Shift+P` → "Python: Select Interpreter").
4. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
5. Copy `.env.example` to `.env` and fill in your real API keys:
   ```
   cp .env.example .env
   ```
   - Get a Gemini API key from Google AI Studio.
   - Get a Tavily API key from tavily.com (free tier available).
6. Run the app:
   ```
   streamlit run app.py
   ```

## Project structure
- `app.py` — Streamlit UI
- `recipe_engine.py` — Gemini prompt, recipe generation, shopping list logic, optional Tavily search
- `.env` — your API keys (never commit this)
- `requirements.txt` — dependencies

## Next steps to extend
- Add a small synthetic recipe dataset as a fallback if the Gemini call fails.
- Add conversation history so users can ask follow-up questions ("make it spicier").
- Add a dietary-safety disclaimer if allergies are ever involved.
