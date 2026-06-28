import streamlit as st
import subprocess
import pandas as pd
import json
import main

# --- PAGE CONFIG ---
st.set_page_config(page_title="Sales Engine", page_icon="🚀", layout="wide")

st.markdown("""
    <style>
    .big-font { font-size:24px !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚀 Sales Engine Control Center")
st.markdown("<p class='big-font'>Manage your Territory Sales Pipeline</p>", unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---
def launch_terminal_task(task_name):
    """Spawns a new Windows PowerShell window running the specific main.py function."""
    cmd = f'start powershell -NoExit -Command "python -c \\"import main; {task_name}\\""'
    subprocess.Popen(cmd, shell=True)
    st.success(f"Launching task in a dedicated terminal window...")

# --- LOAD SETTINGS ---
settings = main.load_settings()

# --- SIDEBAR NAV ---
menu = st.sidebar.radio("Navigation", ["Dashboard", "Manage Brands", "Dispatch Engine"])

# --- UI LOGIC ---
if menu == "Dashboard":
    st.subheader("📊 Live Territory Performance")
    st.info("Performance charts integration pending...")

elif menu == "Manage Brands":
    st.subheader("🍾 Portfolio Configuration")
    
    # Display the brand table
    brand_df = pd.DataFrame.from_dict(settings["brands"], orient="index")
    st.table(brand_df)
    
    st.write("---")
    st.write("Click below to edit your brands in the Terminal Admin Console.")
    if st.button("Edit Brands"):
        launch_terminal_task("main.manage_brands(main.load_settings())")

elif menu == "Dispatch Engine":
    st.subheader("📡 Dispatch Control")
    st.warning("Ensure WhatsApp Desktop is open.")
    
    if st.button("🚀 Start Dispatch Pipeline"):
        launch_terminal_task("main.run_dispatch_engine(main.load_settings())")