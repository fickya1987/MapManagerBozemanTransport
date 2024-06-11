import streamlit as st
from MapManagerBozemanTransport.components.menu import menu_with_redirect
import pandas as pd
from io import BytesIO
from st_supabase_connection import SupabaseConnection

# Redirect to app.py if not logged in, otherwise show the navigation menu
menu_with_redirect()

# Verify the user's role
if st.session_state.authentication_status is not True:
    st.warning("You do not have permission to view this page.")
    st.stop()

# Supabase configuration
SUPABASE_URL = 'https://ikydcpgpuvgdynwaedyw.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlreWRjcGdwdXZnZHlud2FlZHl3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MTgwMzk1MTIsImV4cCI6MjAzMzYxNTUxMn0.zxaiwjcjsi2rPgIq8uEVKhi_5AxVJeu1S2W-Z2yhBWA'
supabase = SupabaseConnection(SUPABASE_URL, SUPABASE_KEY)

required_files = ['stops.txt', 'stop_times.txt', 'trips.txt', 'routes.txt', 'calendar_attributes.txt']

def check_uploaded_files(uploaded_files):
    uploaded_file_names = [file.name for file in uploaded_files]
    status = {file: (file in uploaded_file_names) for file in required_files}
    return status

@st.cache_data
def load_and_process_files(uploaded_files):
    # Initialize dictionary to hold dataframes
    dataframes = {}
    for file in uploaded_files:
        if file.name == 'stops.txt':
            dataframes['stops'] = pd.read_csv(file, delimiter=',')
        elif file.name == 'stop_times.txt':
            dataframes['stop_times'] = pd.read_csv(file, delimiter=',')
        elif file.name == 'trips.txt':
            dataframes['trips'] = pd.read_csv(file, delimiter=',')
        elif file.name == 'routes.txt':
            dataframes['routes'] = pd.read_csv(file, delimiter=',')
        elif file.name == 'calendar_attributes.txt':
            dataframes['calendar_attributes'] = pd.read_csv(file, delimiter=',')
    
    # Perform processing
    stops = dataframes['stops'][['stop_id', 'stop_name', 'stop_lat', 'stop_lon']]
    stop_times = dataframes['stop_times'][['stop_id', 'trip_id', 'arrival_time', 'stop_sequence', 'shape_dist_traveled']]
    trips = dataframes['trips'][['route_id', 'trip_id', 'service_id', 'trip_headsign', 'direction_id', 'shape_id']]
    routes = dataframes['routes'][['route_id', 'route_long_name', 'route_color']]
    calendar_attributes = dataframes['calendar_attributes']

    # Merge trips and routes
    routes_by_trip = pd.merge(trips, routes, on='route_id', how='left').drop_duplicates(subset=['trip_id'], keep='first')

    # Merge stops and stop times
    stop_time_loc = pd.merge(stop_times, stops, on='stop_id', how='left')

    # Merge stops and routes
    stop_data = pd.merge(stop_time_loc, routes_by_trip, on='trip_id', how='left')

    # Merge calendar attributes with service ID for all stops
    stop_data_service = pd.merge(stop_data, calendar_attributes, on='service_id', how='left')

    return stop_data_service

def fetch_supabase_data(files_to_fetch):
    data = {}
    for table_name in files_to_fetch:
        response = supabase.table(table_name).select('*').execute()
        if response.status_code == 200:
            data[table_name] = pd.DataFrame(response.data)
        else:
            st.error(f"Failed to fetch data from {table_name}.")
    return data

def processing_page():
    st.title("Processing Page")
    
    # Allow user to specify which files to load
    st.subheader("Select files that you will upload")
    selected_files = [file for file in required_files if st.checkbox(file)]

    # File uploader
    st.subheader("Upload Selected Files")
    uploaded_files = st.file_uploader("Upload Google Maps Files", accept_multiple_files=True, type="txt")

    if uploaded_files:
        # Check uploaded files status against selected files
        status = check_uploaded_files(uploaded_files)
        for file in selected_files:
            if status.get(file, False):
                st.success(f"{file} uploaded successfully.")
            else:
                st.error(f"{file} is missing.")

        if all(status[file] for file in selected_files):
            # Load and process files
            stop_data_service = load_and_process_files(uploaded_files)
            st.session_state['stop_data_service'] = stop_data_service
            st.success("All files processed successfully!")
            st.write("Processed Data Preview:")
            st.dataframe(stop_data_service.head())  # Display the first few rows of the processed data
        else:
            st.warning("Please upload all selected files to proceed.")

    # Determine which files to fetch from Supabase
    files_to_fetch = [file.split('.')[0] for file in required_files if file not in selected_files]

    # Button to fetch data from Supabase
    if st.button('Fetch Data from Supabase'):
        supabase_data = fetch_supabase_data(files_to_fetch)
        if supabase_data:
            st.session_state['supabase_data'] = supabase_data
            st.success("Data fetched from Supabase successfully!")
            for table_name, dataframe in supabase_data.items():
                st.write(f"Data from {table_name}:")
                st.dataframe(dataframe.head())  # Display the first few rows of the fetched data

if __name__ == "__main__":
    processing_page()
