import streamlit as st
import main
import pandas as pd
import json

st.set_page_config(page_title="Sales Engine", page_icon="🚀", layout="wide")

# Custom CSS for the "Big Font" minimal look
st.markdown("""
    <style>
    .big-font { font-size:24px !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚀 Sales Engine Control Center")
st.markdown("<p class='big-font'>Manage your Territory Sales Pipeline</p>", unsafe_allow_html=True)

settings = main.load_settings()

# Sidebar for Navigation
menu = st.sidebar.radio("Navigation", ["Dashboard", "Manage Brands", "Dispatch Engine"])

if menu == "Dashboard":
    st.subheader("📊 Live Territory Performance")
    # Here you can add logic to read the latest sales file and show a st.bar_chart()
    st.info("Performance charts integration pending...")

elif menu == "Manage Brands":
    st.subheader("🍾 Portfolio Configuration")
    
    # Create a cleaner table view for brands
    brand_df = pd.DataFrame.from_dict(settings["brands"], orient="index")
    st.table(brand_df)
    
    if st.button("Add/Edit Brands via Terminal Menu"):
        # This triggers the existing logic in your terminal
        main.manage_brands(settings)
        st.rerun()

elif menu == "Dispatch Engine":
    st.subheader("📡 Dispatch Control")
    st.warning("Ensure WhatsApp Desktop is open.")
    
    if st.button("🚀 Execute Sales Dispatch"):
        with st.spinner("Processing dispatch engine..."):
            main.run_dispatch_engine(settings)
            st.success("Dispatch process finished!")