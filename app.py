import os
import streamlit as st
from PIL import Image
from google import genai
from google.genai import types

# Backend & API
def get_gemini_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        st.error("Error: GEMINI_API_KEY not found")
        st.stop()
    return genai.Client(api_key = api_key)

