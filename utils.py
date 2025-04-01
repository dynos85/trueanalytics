import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import streamlit as st
from io import BytesIO
import functools

# Use caching to speed up data processing
@functools.lru_cache(maxsize=100)
def parse_date(date_string):
    """Parse date string from CSV into datetime object."""
    try:
        # First try the format DD-MM-YYYY HH:MM:SS
        return pd.to_datetime(date_string, format='%d-%m-%Y %H:%M:%S')
    except:
        try:
            # Then try YYYY-MM-DD HH:MM:SS
            return pd.to_datetime(date_string)
        except:
            # Try a more flexible approach
            return pd.to_datetime(date_string, errors='coerce')

def load_and_process_csv(uploaded_files):
    """
    Load and process uploaded CSV files with optimized performance.
    Returns a combined DataFrame with proper column names.
    """
    if not uploaded_files:
        return None

    all_data = []

    for uploaded_file in uploaded_files:
        try:
            # Optimized CSV reading
            data = pd.read_csv(
                uploaded_file,
                low_memory=False,  # Avoid dtype guessing on chunks
                engine='c'         # Use C engine for faster parsing
            )

            # Determine if the CSV has headers by checking column names
            if all(col.startswith('Unnamed') for col in data.columns) or all(isinstance(col, int) for col in data.columns):
                data = pd.read_csv(
                    uploaded_file, 
                    header=None,
                    low_memory=False,
                    engine='c'
                )

            # Map columns to expected names based on position
            column_mapping = {
                0: 'Test_date_time',  # Column A
                1: 'Profile_id',      # Column B
                3: 'Test_result',     # Column D
                4: 'Test_status',     # Column E
                5: 'Lab_name',        # Column F
                8: 'Truelab_id',      # Column I
                9: 'Lot'              # Column J
            }

            # Filter only required columns for better performance
            try:
                # Select only the required columns and rename them
                required_columns = list(column_mapping.keys())
                data = data.iloc[:, required_columns]
                data.columns = list(column_mapping.values())

                all_data.append(data)
            except Exception as e:
                st.warning(f"Error processing columns: {str(e)}. Trying alternative method...")

                # Alternative method if column selection fails
                new_df = pd.DataFrame()
                for col_idx, col_name in column_mapping.items():
                    if col_idx < len(data.columns):
                        new_df[col_name] = data.iloc[:, col_idx]
                    else:
                        new_df[col_name] = None

                all_data.append(new_df)

        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            continue

    if not all_data:
        return None

    # Combine all dataframes
    with st.spinner("Combining data and processing dates..."):
        combined_df = pd.concat(all_data, ignore_index=True)

        # Convert date column to datetime more efficiently
        combined_df['Test_date_time'] = pd.to_datetime(combined_df['Test_date_time'], errors='coerce')
        combined_df = combined_df.dropna(subset=['Test_date_time'])

        # Add month and week columns for analysis - more efficient strftime
        combined_df['Month'] = pd.DatetimeIndex(combined_df['Test_date_time']).strftime('%Y-%m')
        combined_df['Week'] = pd.DatetimeIndex(combined_df['Test_date_time']).strftime('%Y-%U')

    return combined_df

def get_profile_ids(df):
    """Extract unique profile IDs from the dataframe."""
    if df is None:
        return []
    return sorted(df['Profile_id'].unique().tolist())

@functools.lru_cache(maxsize=32)
def profile_id_analysis(df_hash, selected_profile_id=None):
    """
    Generate Profile ID Analysis.

    Returns:
    - summary_data: Overall summary statistics
    - lab_analysis: Analysis by lab

    Note: df_hash is used for caching purposes. Pass hash(tuple(df)) as df_hash.
    """
    # In actual implementation, we can't cache the dataframe directly
    # so we convert df_hash back to dataframe reference
    df = st.session_state.data

    if df is None or df.empty:
        return None, None

    # Filter by Profile ID if specified
    with st.spinner("Analyzing profile data..."):
        if selected_profile_id and selected_profile_id != "All":
            df = df[df['Profile_id'] == selected_profile_id]

        if df.empty:
            return None, None

        # Compute status counts more efficiently using value_counts
        status_counts = df['Test_status'].value_counts()
        total_runs = len(df)
        total_invalids = status_counts.get('Invalid', 0)
        total_indeterminates = status_counts.get('Indeterminate', 0)
        invalid_indeterminate_percent = ((total_invalids + total_indeterminates) / total_runs * 100) if total_runs > 0 else 0

        summary_data = {
            'Total Runs': total_runs,
            'Total Invalids': total_invalids,
            'Total Indeterminates': total_indeterminates,
            'Overall Invalid/Indeterminate %': round(invalid_indeterminate_percent, 2)
        }

        # Prepare lab-wise analysis - more efficiently using groupby
        # Use value_counts and crosstab for faster computation
        lab_data = []

        for lab_name in df['Lab_name'].unique():
            lab_df = df[df['Lab_name'] == lab_name]
            total_tests = len(lab_df)

            # Get status and result counts more efficiently
            lab_status_counts = lab_df['Test_status'].value_counts()
            lab_result_counts = lab_df['Test_result'].value_counts()

            total_detected = lab_result_counts.get('Detected', 0)
            total_invalid = lab_status_counts.get('Invalid', 0)
            total_indeterminate = lab_status_counts.get('Indeterminate', 0)

            invalid_percent = ((total_invalid + total_indeterminate) / total_tests * 100) if total_tests > 0 else 0

            # Calculate last 10 entries invalid percentage (changed from first 10)
            last_10 = lab_df.tail(10)
            if not last_10.empty:
                last_10_status_counts = last_10['Test_status'].value_counts()
                last_10_total = len(last_10)
                last_10_invalid = last_10_status_counts.get('Invalid', 0)
                last_10_indeterminate = last_10_status_counts.get('Indeterminate', 0)
                last_10_invalid_percent = ((last_10_invalid + last_10_indeterminate) / last_10_total * 100) if last_10_total > 0 else 0
            else:
                last_10_invalid_percent = 0

            # Get unique Truelab IDs for this lab - more efficiently
            truelab_ids = ', '.join(lab_df['Truelab_id'].drop_duplicates().astype(str).tolist())

            lab_data.append({
                'Lab Name': lab_name,
                'Truelab ID': truelab_ids,
                'Total Tests': total_tests,
                'Total Detected': total_detected,
                'Total Invalid/Indeterminate': total_invalid + total_indeterminate,
                'Invalid/Indeterminate %': round(invalid_percent, 2),
                'Last 10 runs Invalid/Indeterminate %': round(last_10_invalid_percent, 2)
            })

    return summary_data, pd.DataFrame(lab_data)

def lot_specific_analysis(df, selected_profile_id=None):
    """Generate Lot Specific Analysis."""
    if df is None or df.empty:
        return None, None

    # Filter by Profile ID if specified
    if selected_profile_id and selected_profile_id != "All":
        df = df[df['Profile_id'] == selected_profile_id]

    if df.empty:
        return None, None

    lot_data = []

    for lot_number in df['Lot'].unique():
        lot_df = df[df['Lot'] == lot_number]
        total_runs = len(lot_df)
        total_invalid = lot_df[lot_df['Test_status'] == 'Invalid'].shape[0]
        total_indeterminate = lot_df[lot_df['Test_status'] == 'Indeterminate'].shape[0]

        invalid_percent = ((total_invalid + total_indeterminate) / total_runs * 100) if total_runs > 0 else 0

        lot_data.append({
            'Lot Number': lot_number,
            'Total Runs': total_runs,
            'Total Invalid/Indeterminate': total_invalid + total_indeterminate,
            'Invalid/Indeterminate %': round(invalid_percent, 2)
        })

    lot_df = pd.DataFrame(lot_data)

    # Create graph data for top 20 lots based on total tests
    if not lot_df.empty and len(lot_df) > 0:
        top_lots = lot_df.sort_values('Total Runs', ascending=False).head(20)
        return lot_df, top_lots
    else:
        return lot_df, None

def trend_analysis(df, selected_profile_id=None, selected_lab=None):
    """Generate Trend Analysis data for visualizations."""
    if df is None or df.empty:
        return None, None

    # Filter by Profile ID if specified
    if selected_profile_id and selected_profile_id != "All":
        df = df[df['Profile_id'] == selected_profile_id]

    # Filter by Lab Name if specified
    if selected_lab and selected_lab != "All Labs":
        df = df[df['Lab_name'] == selected_lab]

    if df.empty:
        return None, None

    # Monthly trend analysis
    monthly_data = df.groupby('Month').agg(
        Total_Runs=('Test_date_time', 'count'),
        Total_Invalid=('Test_status', lambda x: (x == 'Invalid').sum()),
        Total_Indeterminate=('Test_status', lambda x: (x == 'Indeterminate').sum())
    ).reset_index()

    monthly_data['Total_Invalid_Indeterminate'] = monthly_data['Total_Invalid'] + monthly_data['Total_Indeterminate']
    monthly_data['Month'] = pd.to_datetime(monthly_data['Month'] + '-01')
    monthly_data = monthly_data.sort_values('Month')

    # Weekly trend analysis
    weekly_data = df.groupby('Week').agg(
        Total_Runs=('Test_date_time', 'count'),
        Total_Invalid=('Test_status', lambda x: (x == 'Invalid').sum()),
        Total_Indeterminate=('Test_status', lambda x: (x == 'Indeterminate').sum())
    ).reset_index()

    weekly_data['Total_Invalid_Indeterminate'] = weekly_data['Total_Invalid'] + weekly_data['Total_Indeterminate']
    weekly_data['Week'] = pd.to_datetime(weekly_data['Week'].apply(lambda x: f"{x.split('-')[0]}-W{x.split('-')[1]}-1"), format='%Y-W%U-%w')
    weekly_data = weekly_data.sort_values('Week')

    return monthly_data, weekly_data

def weekly_analysis(df, selected_profile_id=None, selected_lab=None):
    """Generate Weekly Analysis by lab."""
    if df is None or df.empty:
        return None

    # Filter by Profile ID if specified
    if selected_profile_id and selected_profile_id != "All":
        df = df[df['Profile_id'] == selected_profile_id]

    # Filter by Lab Name if specified
    if selected_lab and selected_lab != "All Labs":
        df = df[df['Lab_name'] == selected_lab]

    if df.empty:
        return None

    weekly_lab_data = []

    # Group by week and lab name
    for week in sorted(df['Week'].unique()):
        week_df = df[df['Week'] == week]
        
        try:
            # Week format is expected to be 'YYYY-WW'
            year = week.split('-')[0]
            week_num = week.split('-')[1]
            
            # Calculate the start date (Monday) for this week
            week_start = pd.to_datetime(f"{year}-{week_num}-1", format="%Y-%U-%w")
            week_end = week_start + pd.Timedelta(days=6)  # This gives us Sunday
            date_range = f"{week_start.strftime('%d-%m-%Y')} to {week_end.strftime('%d-%m-%Y')}"
        except (IndexError, ValueError) as e:
            # Fallback if date parsing fails
            date_range = f"Week {week}"

        for lab_name in week_df['Lab_name'].unique():
            lab_week_df = week_df[week_df['Lab_name'] == lab_name]

            total_runs = len(lab_week_df)
            total_invalid = lab_week_df[lab_week_df['Test_status'] == 'Invalid'].shape[0]
            total_indeterminate = lab_week_df[lab_week_df['Test_status'] == 'Indeterminate'].shape[0]

            invalid_percent = ((total_invalid + total_indeterminate) / total_runs * 100) if total_runs > 0 else 0

            # Convert week format to a more readable format (Year-Week)
            week_display = f"{week.split('-')[0]} Week {week.split('-')[1]}"

            weekly_lab_data.append({
                'Week': week_display,
                'Date Range': date_range,
                'Lab Name': lab_name,
                'Total Runs': total_runs,
                'Total Invalid/Indeterminate': total_invalid + total_indeterminate,
                'Invalid/Indeterminate %': round(invalid_percent, 2)
            })

    # Create DataFrame and sort by Lab Name
    df_result = pd.DataFrame(weekly_lab_data)
    return df_result.sort_values('Lab Name') if not df_result.empty else df_result

def export_to_csv(df):
    """Export dataframe to CSV for download."""
    output = BytesIO()
    df.to_csv(output, index=False)
    return output.getvalue()

def create_monthly_trend_chart(monthly_data):
    """Create monthly trend chart using plotly with bar for Total Runs and line for Invalid/Indeterminate."""
    if monthly_data is None or monthly_data.empty:
        return None

    fig = go.Figure()

    # Add bar for Total Runs
    fig.add_trace(go.Bar(
        x=monthly_data['Month'],
        y=monthly_data['Total_Runs'],
        name='Total Runs',
        marker_color='#4E79A7'
    ))

    # Add line for Total Invalid/Indeterminate
    fig.add_trace(go.Scatter(
        x=monthly_data['Month'],
        y=monthly_data['Total_Invalid_Indeterminate'],
        mode='lines+markers',
        name='Total Invalid/Indeterminate',
        line=dict(color='#F28E2B', width=2),
        marker=dict(size=8)
    ))

    # Update layout with light theme
    fig.update_layout(
        title='Monthly Trend Analysis',
        xaxis_title='Month',
        yaxis_title='Count',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=500
    )

    # Update grid and axes
    fig.update_xaxes(showline=True, linewidth=1, gridcolor='rgba(0, 0, 0, 0.1)')
    fig.update_yaxes(showline=True, linewidth=1, gridcolor='rgba(0, 0, 0, 0.1)')

    return fig

def create_weekly_trend_chart(weekly_data):
    """Create weekly trend chart using plotly with bar for Total Runs and line for Invalid/Indeterminate."""
    if weekly_data is None or weekly_data.empty:
        return None

    fig = go.Figure()

    # Add bar for Total Runs
    fig.add_trace(go.Bar(
        x=weekly_data['Week'],
        y=weekly_data['Total_Runs'],
        name='Total Runs',
        marker_color='#76B7B2'
    ))

    # Add line for Total Invalid/Indeterminate
    fig.add_trace(go.Scatter(
        x=weekly_data['Week'],
        y=weekly_data['Total_Invalid_Indeterminate'],
        mode='lines+markers',
        name='Total Invalid/Indeterminate',
        line=dict(color='#E15759', width=2),
        marker=dict(size=8)
    ))

    # Update layout with light theme
    fig.update_layout(
        title='Weekly Trend Analysis',
        xaxis_title='Week',
        yaxis_title='Count',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=500
    )

    # Update grid and axes
    fig.update_xaxes(showline=True, linewidth=1, gridcolor='rgba(0, 0, 0, 0.1)')
    fig.update_yaxes(showline=True, linewidth=1, gridcolor='rgba(0, 0, 0, 0.1)')

    return fig

def create_top_lots_chart(top_lots_data):
    """Create chart for top 20 lots by total runs with invalid percentage."""
    if top_lots_data is None or top_lots_data.empty:
        return None

    fig = go.Figure()

    # Sort by Total Runs for display
    df = top_lots_data.sort_values('Total Runs', ascending=True)

    # Add bar for Total Runs
    fig.add_trace(go.Bar(
        x=df['Total Runs'],
        y=df['Lot Number'],
        name='Total Runs',
        orientation='h',
        marker_color='#6236FF'
    ))

    # Create a secondary axis for the Invalid/Indeterminate percentage as a line chart
    fig.add_trace(go.Scatter(
        x=df['Invalid/Indeterminate %'],
        y=df['Lot Number'],
        mode='lines+markers',
        name='Invalid/Indeterminate %',
        line=dict(color='#FF3366', width=2),
        marker=dict(size=8)
    ))

    # Update layout with light theme
    fig.update_layout(
        title='Top 20 Lots by Total Runs',
        xaxis_title='Total Runs',
        yaxis_title='Lot Number',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=600,
        margin=dict(l=150)  # Add more margin on the left for lot numbers
    )

    # Update grid and axes
    fig.update_xaxes(showline=True, linewidth=1, gridcolor='rgba(0, 0, 0, 0.1)')
    fig.update_yaxes(showline=True, linewidth=1, gridcolor='rgba(0, 0, 0, 0.1)')

    return fig