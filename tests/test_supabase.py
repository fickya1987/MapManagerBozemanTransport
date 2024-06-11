import streamlit as st
from supabase import create_client, Client
from st_supabase_connection import SupabaseConnection, execute_query

# Initialize connection using secrets
supabase_url = st.secrets["connections"]["supabase"]["SUPABASE_URL"]
supabase_key = st.secrets["connections"]["supabase"]["SUPABASE_KEY"]
supabase: Client = create_client(supabase_url, supabase_key)

# Function to verify connection
def verify_connection() -> bool:
    try:
        # Perform a simple query to verify connection
        query = supabase.table("routes").select("*").limit(1)
        response = execute_query(query, ttl="10m")
        if response and response.data:
            st.write("Connection successful!")
            return True
        else:
            st.write("Connection failed or no data retrieved.")
            st.write(f"Response: {response}")
            return False
    except Exception as e:
        st.write(f"An error occurred: {e}")
        return False

# Function to list all tables
def list_tables() -> bool:
    try:
        query = supabase.rpc("pg_catalog.pg_tables").select("tablename")
        response = execute_query(query)
        if response and response.data:
            st.write("Tables in database:")
            tables = [row['tablename'] for row in response.data]
            for table in tables:
                st.write(table)
            return True
        else:
            st.write("Failed to retrieve tables.")
            return False
    except Exception as e:
        st.write(f"An error occurred while listing tables: {e}")
        return False

def main():
    st.title("Supabase Database Interaction")

    # Verify connection to the database
    if verify_connection():
        # List all tables in the database
        if list_tables():
            st.write("Successfully listed all tables.")
        else:
            st.write("Failed to list tables.")
    else:
        st.write("Connection to the database failed.")

if __name__ == "__main__":
    main()
