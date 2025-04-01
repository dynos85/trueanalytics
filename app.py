import streamlit as st
import pandas as pd
import numpy as np
from utils import (load_and_process_csv, get_profile_ids, profile_id_analysis, 
                  lot_specific_analysis, trend_analysis, weekly_analysis, 
                  export_to_csv, create_monthly_trend_chart, create_weekly_trend_chart,
                  create_top_lots_chart)

# Set up page configuration
st.set_page_config(
    page_title="Truenat Dashboard Data Analysis Tool",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom styling for the sidebar and container
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&family=Space+Grotesk:wght@500;700&display=swap');
    
    /* Make the sidebar thinner */
    [data-testid="stSidebar"] {
        min-width: 220px;
        max-width: 220px;
    }
    
    /* Sidebar title padding */
    [data-testid="stSidebar"] .css-1d391kg {
        padding-top: 1rem;
        font-family: 'Space Grotesk', sans-serif;
    }
    
    /* Container styling */
    .block-container {
        max-width: 1200px;
        padding-top: 2rem;
        padding-bottom: 1rem;
        font-family: 'Poppins', sans-serif;
    }
    
    /* Style for buttons */
    .stButton button {
        background-color: #4e8cff;
        color: white;
        font-family: 'Poppins', sans-serif;
        font-weight: 600;
    }

    h1, h2, h3 {
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 700;
    }

    p {
        font-family: 'Poppins', sans-serif;
        font-weight: 400;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state variables if not exists
if 'data' not in st.session_state:
    st.session_state.data = None
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'home'
if 'profile_ids' not in st.session_state:
    st.session_state.profile_ids = []
if 'lab_names' not in st.session_state:
    st.session_state.lab_names = []
if 'selected_profile_id' not in st.session_state:
    st.session_state.selected_profile_id = "All"
if 'selected_lab' not in st.session_state:
    st.session_state.selected_lab = "All Labs"

# Navigation functions
def navigate_to(page):
    st.session_state.current_page = page
    if page == 'home':
        # Reset all filters when going to home
        st.session_state.selected_profile_id = "All"
        st.session_state.selected_lab = "All Labs"
        # Ensure page gets fully reloaded to hide sidebar
        st.rerun()
    
# Sidebar for navigation - only show if not on home page
if st.session_state.current_page != 'home':
    with st.sidebar:
        # App title and author
        st.markdown("""
        <div style='text-align: center; margin-bottom: 20px;'>
            <h2 style='font-size: 1.5em;'>Truenat Data Analysis Tool</h2>
            <p>Designed by Subhadeep.S</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Home button at the top
        if st.button("🏠 Home", key="home_sidebar"):
            navigate_to('home')
        
        st.divider()
    
    with st.sidebar:
        # Only show analysis options if data is loaded
        if st.session_state.data is not None:
            # Profile ID selector - moved above Analysis Sections
            st.subheader("Filter Data")
            
            # Profile ID filter
            profile_options = ["All"] + st.session_state.profile_ids
            selected_profile = st.selectbox(
                "Select Profile ID",
                profile_options,
                index=profile_options.index(st.session_state.selected_profile_id) if st.session_state.selected_profile_id in profile_options else 0
            )
            
            if selected_profile != st.session_state.selected_profile_id:
                st.session_state.selected_profile_id = selected_profile
                st.rerun()
                
            # Lab name filter
            if st.session_state.lab_names:
                lab_options = ["All Labs"] + st.session_state.lab_names
                selected_lab = st.selectbox(
                    "Select Lab",
                    lab_options,
                    index=lab_options.index(st.session_state.selected_lab) if st.session_state.selected_lab in lab_options else 0
                )
                
                if selected_lab != st.session_state.selected_lab:
                    st.session_state.selected_lab = selected_lab
                    st.rerun()
                    
            st.divider()
            
            # Analysis Section buttons
            st.subheader("Analysis Sections")
            
            if st.button("Profile ID Analysis", key="profile_sidebar"):
                navigate_to('profile_id_analysis')
                
            if st.button("Lot Specific Analysis", key="lot_sidebar"):
                navigate_to('lot_analysis')
                
            if st.button("Trend Analysis", key="trend_sidebar"):
                navigate_to('trend_analysis')
                
            if st.button("Weekly Analysis", key="weekly_sidebar"):
                navigate_to('weekly_analysis')

# Home Page
def render_home_page():
    col1, col2, col3 = st.columns([1, 3, 1])
    
    with col2:
        st.markdown("""
        <div style='text-align: center; padding: 40px 0;'>
            <h1 style='font-size: 3em;'>Truenat Dashboard Data Analysis Tool</h1>
            <p style='font-size: 1.2em; margin-top: 20px;'>Designed by Subhadeep. S</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        st.markdown("""
        <div style='text-align: center; padding: 20px 0;'>
            <h2>Upload your CSV data files to begin analysis</h2>
        </div>
        """, unsafe_allow_html=True)
        
        uploaded_files = st.file_uploader("Upload one or more CSV files", 
                                          type=["csv"], 
                                          accept_multiple_files=True)
        
        if uploaded_files:
            with st.spinner("Processing CSV files..."):
                data = load_and_process_csv(uploaded_files)
                if data is not None and not data.empty:
                    st.session_state.data = data
                    st.session_state.profile_ids = get_profile_ids(data)
                    
                    # Get unique lab names from data
                    if 'Lab_name' in data.columns:
                        st.session_state.lab_names = sorted(data['Lab_name'].unique().tolist())
                    else:
                        st.session_state.lab_names = []
                        
                    st.success(f"Successfully loaded {len(data)} records from {len(uploaded_files)} file(s).")
                    
                    st.markdown("---")
                    st.markdown("<h3 style='text-align: center;'>Select an analysis section to continue</h3>", unsafe_allow_html=True)
                    
                    # Analysis section buttons
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Profile ID Analysis", key="profile_home", use_container_width=True):
                            navigate_to('profile_id_analysis')
                        if st.button("Trend Analysis", key="trend_home", use_container_width=True):
                            navigate_to('trend_analysis')
                    with col2:
                        if st.button("Lot Specific Analysis", key="lot_home", use_container_width=True):
                            navigate_to('lot_analysis')
                        if st.button("Weekly Analysis", key="weekly_home", use_container_width=True):
                            navigate_to('weekly_analysis')
                else:
                    st.error("Error processing the uploaded files. Please make sure they have the correct format.")

# Profile ID Analysis Page
def render_profile_id_analysis():
    st.title("Profile ID Analysis")
    
    # Add home button at the top
    if st.button("🏠 Home", key="home_profile"):
        navigate_to('home')
    
    st.markdown("---")
    
    if st.session_state.data is None:
        st.warning("No data loaded. Please upload CSV files from the home page.")
        return
    
    # Get analysis results - use dataframe hash for caching
    df_hash = hash(tuple(map(tuple, st.session_state.data.values))) if st.session_state.data is not None else None
    summary_data, lab_analysis = profile_id_analysis(
        df_hash, 
        st.session_state.selected_profile_id
    )
    
    if summary_data is None or lab_analysis is None:
        st.warning("No data available for the selected Profile ID.")
        return
    
    # Display Profile ID summary
    st.subheader(f"Profile ID Summary: {st.session_state.selected_profile_id}")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Runs", summary_data['Total Runs'])
    with col2:
        st.metric("Total Invalids", summary_data['Total Invalids'])
    with col3:
        st.metric("Total Indeterminates", summary_data['Total Indeterminates'])
    with col4:
        st.metric("Overall Invalid/Indeterminate %", f"{summary_data['Overall Invalid/Indeterminate %']}%")
    
    st.markdown("---")
    
    # Display lab analysis table
    st.subheader("Lab-wise Analysis")
    
    if lab_analysis.empty:
        st.info("No lab data available for the selected profile.")
    else:
        st.dataframe(lab_analysis, use_container_width=True, height=400)
        
        # Download button for lab analysis
        lab_csv = export_to_csv(lab_analysis)
        st.download_button(
            label="Download Lab Analysis CSV",
            data=lab_csv,
            file_name=f"profile_id_analysis_{st.session_state.selected_profile_id}.csv",
            mime="text/csv"
        )

# Lot Specific Analysis Page
def render_lot_analysis():
    st.title("Lot Specific Analysis")
    
    # Add home button at the top
    if st.button("🏠 Home", key="home_lot"):
        navigate_to('home')
    
    st.markdown("---")
    
    if st.session_state.data is None:
        st.warning("No data loaded. Please upload CSV files from the home page.")
        return
    
    # Get lot analysis results
    lot_analysis, top_lots = lot_specific_analysis(
        st.session_state.data, 
        st.session_state.selected_profile_id
    )
    
    if lot_analysis is None or lot_analysis.empty:
        st.warning("No lot data available for the selected Profile ID.")
        return
    
    # Display lot analysis table
    st.subheader(f"Lot Analysis: {st.session_state.selected_profile_id}")
    st.dataframe(lot_analysis, use_container_width=True, height=400)
    
    # Top 20 lots chart
    if top_lots is not None and not top_lots.empty:
        st.subheader("Top 20 Lots by Total Tests")
        top_lots_chart = create_top_lots_chart(top_lots)
        if top_lots_chart:
            st.plotly_chart(top_lots_chart, use_container_width=True)
    
    # Download button for lot analysis
    lot_csv = export_to_csv(lot_analysis)
    st.download_button(
        label="Download Lot Analysis CSV",
        data=lot_csv,
        file_name=f"lot_analysis_{st.session_state.selected_profile_id}.csv",
        mime="text/csv"
    )

# Trend Analysis Page
def render_trend_analysis():
    st.title("Trend Analysis")
    
    # Add home button at the top
    if st.button("🏠 Home", key="home_trend"):
        navigate_to('home')
    
    st.markdown("---")
    
    if st.session_state.data is None:
        st.warning("No data loaded. Please upload CSV files from the home page.")
        return
    
    # Show current filters
    profile_filter = st.session_state.selected_profile_id
    lab_filter = st.session_state.selected_lab
    
    st.subheader("Current Filters")
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"Profile ID: {profile_filter}")
    with col2:
        st.info(f"Lab: {lab_filter}")
        
    st.markdown("---")
    
    # Get trend analysis data with lab filter
    monthly_data, weekly_data = trend_analysis(
        st.session_state.data, 
        st.session_state.selected_profile_id,
        st.session_state.selected_lab
    )
    
    if monthly_data is None or weekly_data is None:
        st.warning("No trend data available for the selected filters.")
        return
    
    # Create monthly trend chart
    st.subheader("Monthly Trend Analysis")
    monthly_chart = create_monthly_trend_chart(monthly_data)
    if monthly_chart:
        st.plotly_chart(monthly_chart, use_container_width=True)
        
        # Download button for monthly data
        monthly_csv = export_to_csv(monthly_data)
        st.download_button(
            label="Download Monthly Trend Data",
            data=monthly_csv,
            file_name=f"monthly_trend_{profile_filter}_{lab_filter.replace(' ', '_')}.csv",
            mime="text/csv"
        )
    
    st.markdown("---")
    
    # Create weekly trend chart
    st.subheader("Weekly Trend Analysis")
    weekly_chart = create_weekly_trend_chart(weekly_data)
    if weekly_chart:
        st.plotly_chart(weekly_chart, use_container_width=True)
        
        # Download button for weekly data
        weekly_csv = export_to_csv(weekly_data)
        st.download_button(
            label="Download Weekly Trend Data",
            data=weekly_csv,
            file_name=f"weekly_trend_{profile_filter}_{lab_filter.replace(' ', '_')}.csv",
            mime="text/csv"
        )

# Weekly Analysis Page
def render_weekly_analysis():
    st.title("Weekly Analysis")
    
    # Add home button at the top
    if st.button("🏠 Home", key="home_weekly"):
        navigate_to('home')
    
    st.markdown("---")
    
    if st.session_state.data is None:
        st.warning("No data loaded. Please upload CSV files from the home page.")
        return
    
    # Show current filters
    profile_filter = st.session_state.selected_profile_id
    lab_filter = st.session_state.selected_lab
    
    st.subheader("Current Filters")
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"Profile ID: {profile_filter}")
    with col2:
        st.info(f"Lab: {lab_filter}")
        
    st.markdown("---")
    
    # Get weekly analysis results with lab filter
    weekly_analysis_data = weekly_analysis(
        st.session_state.data, 
        st.session_state.selected_profile_id,
        st.session_state.selected_lab
    )
    
    if weekly_analysis_data is None or weekly_analysis_data.empty:
        st.warning("No weekly data available for the selected filters.")
        return
    
    # Display weekly analysis table
    lab_text = "" if lab_filter == "All Labs" else f" for {lab_filter}"
    st.subheader(f"Weekly Analysis by Lab{lab_text}")
    st.dataframe(weekly_analysis_data, use_container_width=True, height=500)
    
    # Download button for weekly analysis
    weekly_csv = export_to_csv(weekly_analysis_data)
    st.download_button(
        label="Download Weekly Analysis CSV",
        data=weekly_csv,
        file_name=f"weekly_analysis_{profile_filter}_{lab_filter.replace(' ', '_')}.csv",
        mime="text/csv"
    )

# Main application flow
if st.session_state.current_page == 'home':
    render_home_page()
elif st.session_state.current_page == 'profile_id_analysis':
    render_profile_id_analysis()
elif st.session_state.current_page == 'lot_analysis':
    render_lot_analysis()
elif st.session_state.current_page == 'trend_analysis':
    render_trend_analysis()
elif st.session_state.current_page == 'weekly_analysis':
    render_weekly_analysis()
else:
    st.error("Unknown page")
    navigate_to('home')
