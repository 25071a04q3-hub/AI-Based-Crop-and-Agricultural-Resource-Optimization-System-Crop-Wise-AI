"""
FarmTwin — Root Deployment Entrypoint.

Allows standard deployment commands like `streamlit run app.py` or `streamlit run ui/app.py`
to resolve the engine and UI modules seamlessly on Render, Streamlit Cloud, and Docker.
"""
import sys
from pathlib import Path

# Add repo root to Python path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Launch main dashboard
from ui import app
