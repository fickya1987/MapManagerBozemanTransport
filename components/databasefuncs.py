import streamlit as st
import pandas as pd
from supabase import create_client, Client
from st_supabase_connection import SupabaseConnection, execute_query

# Define URL and Key Outside of Any Function
supabase_url = st.secrets["connections"]["supabase"]["SUPABASE_URL"]
supabase_key = st.secrets["connections"]["supabase"]["SUPABASE_KEY"]
columns_to_select = {
    'stops': ['stop_id', 'stop_name', 'stop_lat', 'stop_lon'],
    'stop_times': ['stop_id', 'trip_id', 'arrival_time', 'stop_sequence', 'shape_dist_traveled'],
    'trips': ['route_id', 'trip_id', 'service_id', 'trip_headsign', 'direction_id', 'shape_id'],
    'routes': ['route_id', 'route_long_name', 'route_color'],
    'calendar_attributes': []
}

# Primary keys for each table
primary_keys = {
    'calendar_attributes': 'service_id',
    'routes': 'route_id',
    'stop_times': 'index',
    'stops': 'stop_id',
    'trips': 'trip_id'
}

# Initialize Client Function
def initialize_client(supabase_url=supabase_url, supabase_key=supabase_key):
    try:
        st.session_state["client"] = create_client(supabase_url, supabase_key)
        st.session_state["initialized"] = True
        st.success("Client initialized! - you are connected to the database", icon="✅")
    except Exception as e:
        st.error(f"Client initialization failed: {e}", icon="❌")
        st.session_state["initialized"] = False

# Check Uploaded Files
def check_uploaded_files(uploaded_files, required_files=["routes.txt", "stops.txt", "stop_times.txt", "trips.txt", "calendar_attributes.txt"]):
    uploaded_file_names = [file.name for file in uploaded_files]
    missing_files = [file for file in required_files if file not in uploaded_file_names]
    return missing_files

# Pull Selected Files from Supabase
@st.cache_data
def pull_selected_files(tables, columns):
    data = {}
    dtypes = {}
    for table in tables:
        col_selection = columns.get(table, '*')
        if isinstance(col_selection, list):
            col_selection = ','.join(col_selection)
        st.write(f"Pulling data for table: {table}, columns: {col_selection}")
        query = st.session_state["client"].table(table).select(col_selection)
        response = execute_query(query)
        if response and response.data:
            df = pd.DataFrame(response.data)
            data[table] = df
            dtypes[table] = df.dtypes.to_dict()
            data[table]['source'] = 'database'
    return data, dtypes

# Clean DataFrame
def clean_data(df):
    # Convert 'NULL' strings and empty strings to None
    df = df.replace({'': None, 'NULL': None})
    
    # Convert NaN values to None
    df = df.where(pd.notnull(df), None)
    
    return df

# Upload Table
def upload_table(file, table_name):
    client = st.session_state["client"]
    df = pd.read_csv(file, delimiter=',')
    
    # Clean the DataFrame
    df = clean_data(df)
    
    # Ensure all columns match the expected dtypes from the database
    expected_dtypes = st.session_state["dtypes"].get(table_name, {})
    for col, expected_dtype in expected_dtypes.items():
        if col in df.columns:
            df[col] = df[col].astype(expected_dtype)

    try:
        # Determine the primary key
        primary_key = primary_keys.get(table_name, None)
        
        if len(df) > 500:
            # Add an 'index' column to ensure unique primary key values
            df.reset_index(inplace=True)
            primary_key = 'index'

        # Verify the columns in the uploaded file match the expected columns
        expected_columns = columns_to_select.get(table_name, df.columns.tolist())
        if not set(expected_columns).issubset(df.columns):
            st.error(f"Columns in the uploaded file for {table_name} do not match the expected schema.")
            st.write(f"Expected columns: {expected_columns}")
            st.write(f"Uploaded file columns: {df.columns.tolist()}")
            return

        # Delete all rows in the table using a condition that is always false for a numeric field
        client.table(table_name).delete().neq(primary_key, -1).execute()
        
        # Convert DataFrame to dictionary
        data = df.to_dict(orient='records')

        def clean_row(row):
            for key, value in row.items():
                if pd.isna(value) or value in ('', 'NULL'):
                    row[key] = None
            return row
        
        # Clean each row in the data
        data = [clean_row(row) for row in data]

        # Insert new data into the table in chunks
        for i in range(0, len(data), 500):
            chunk = data[i:i+500]
            client.table(table_name).insert(chunk).execute()
        
        st.success(f"Table {table_name} uploaded successfully.")
    except Exception as e:
        st.error(f"Error occurred while uploading table {table_name}: {e}")

# Main Function for Testing
def main():
    st.title("Supabase Database Interaction")
    st.markdown('''This page allows you to upload google maps files to adjust in the map viewer page. 
                All of the files are stored on a lightweight database, so you can proceed without uploading anything. 
                If you believe that you have an updated copy of one of the following files, then hit that replace table button 
                to permanently replace the particular file.''')
    st.markdown('''**Currently this app operates on files:**
                routes.txt, stops.txt, stop_times,txt, trips.txt, calendar_attributes.txt''')

    # Initialize client
    if "initialized" not in st.session_state or not st.session_state["initialized"]:
        initialize_client()

    required_files = ["routes", "stops", "stop_times", "trips", "calendar_attributes"]
    
    uploaded_files = st.file_uploader("Upload your files", accept_multiple_files=True, type=["txt", "csv"])
    
    # Initialize data_loaded ss
    if "data_loaded" not in st.session_state:
        st.session_state['data_loaded'] = False
    
    # Initialize dtypes ss
    if "dtypes" not in st.session_state:
        st.session_state['dtypes'] = {}

    if st.button("Load Data from Database"):
        st.session_state['data_loaded'] = True
        data, dtypes = pull_selected_files(required_files, columns_to_select)
        st.session_state["dtypes"] = dtypes 

        if uploaded_files:
            # Process uploaded files and replace corresponding data
            for file in uploaded_files:
                table_name = file.name.split('.')[0]
                df = pd.read_csv(file)
                df['source'] = 'uploaded'
                data[table_name] = df

    if st.session_state['data_loaded']:
        st.subheader("Replace Table Data in Database with Upload")
        st.markdown("Click this button if you want the permanently stored files to be replaced by the copy you have uploaded.")
        if uploaded_files:
            replace_selections = {file.name: st.checkbox(file.name, value=True) for file in uploaded_files}

            if st.button("Replace Tables"):
                for file in uploaded_files:
                    if replace_selections[file.name]:
                        table_name = file.name.split('.')[0]
                        upload_table(file, table_name)
        else:
            st.warning("No files uploaded to replace.")

if __name__ == "__main__":
    main()
