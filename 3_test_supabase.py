import streamlit as st
from st_supabase_connection import SupabaseConnection, execute_query

st_supabase_client = st.connection(
    name="YOUR_CONNECTION_NAME",
    type=SupabaseConnection,
    ttl=None,
    url="YOUR_SUPABASE_URL", # not needed if provided as a streamlit secret
    key="YOUR_SUPABASE_KEY", # not needed if provided as a streamlit secret
)

# Initialize connection.
conn = st.connection("supabase", type=SupabaseConnection)

# Debugging: Check connection
try:
    # Attempt to perform a simple query to check the connection
    query = conn.table("routes").select("*")
    response = execute_query(query, ttl="10m")
    
    if response and response.data:
        st.write("Connection successful!")
    else:
        st.write("Connection failed or no data retrieved.")
        st.write(f"Response status code: {response.status_code}")
        st.write(f"Response data: {response.data}")
        st.write(f"Response error: {response.error}")

except Exception as e:
    st.write(f"An error occurred: {e}")

# Print results.
if response and response.data:
    # Print column headers
    if len(response.data) > 0:
        columns = response.data[0].keys()
        st.write(" | ".join(columns))
        st.write("-" * 40)

    # Print each row of data
    for row in response.data:
        row_data = [str(row[col]) for col in columns]
        st.write(" | ".join(row_data))
else:
    st.write("No data retrieved or query failed.")
    st.write(f"Response: {response}")
