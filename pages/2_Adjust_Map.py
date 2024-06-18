import streamlit as st
import folium
from streamlit_folium import st_folium
from streamlit_js_eval import streamlit_js_eval, get_geolocation
from jinja2 import Template
from folium.map import Marker
from components.menu import menu_with_redirect
from components.map import *
from components.databasefuncs import ensure_tables_exist, update_field, propagate_updates

### Set up page ensure logged in ###

# Initialize user session and verify login
menu_with_redirect()

# Verify the user's role
if not st.session_state.get("authentication_status", False):
    st.warning("You do not have permission to view this page.")
    st.stop()

bozeman_coords = [45.6770, -111.0429]

# initialize location session state with fill in coords
if "latitude" not in st.session_state:
    st.session_state["latitude"] = bozeman_coords[0]
if "longitude" not in st.session_state:
    st.session_state["longitude"] = bozeman_coords[1]


def update_location():
    return [st.session_state["latitude"], st.session_state["longitude"]]


# Title
st.title("Live Location Map Updates")

if st.button("Upload Data (previous page)"):
    st.switch_page("pages/1_Upload_Data.py")

    ### Build map and put Bus stops on viewer ###

# Initialize a folium map
m = folium.Map(location=bozeman_coords, zoom_start=14, tiles='cartodbpositron')

# pull processed data from session state
stop_data_service = st.session_state["processed_data"]["stop_data_service"]
bus_lines = organize_by_bus_line(
    stop_data_service)  # organize data by bus line
# user select bus line to view
selected_bus_line = st.selectbox("Select Bus Line", options=bus_lines.keys())

# Add bus stops to the map
if selected_bus_line in bus_lines:
    bus_stops = bus_lines[selected_bus_line]
    unique_stops = bus_stops[['stop_lat', 'stop_lon', 'stop_id',
                              'stop_name', 'interpolated_time']].drop_duplicates()
    for _, stop in unique_stops.iterrows():
        marker = folium.Marker(location=[stop['stop_lat'], stop['stop_lon']],
                               popup=f"{stop['stop_name']} <br>ID:{stop['stop_id']} <br> Time:{stop.get('interpolated_time', 'unknown')}")
        marker.add_to(m)

        ### Live Location ###

loc = get_geolocation()

# Update session state with the live location & Put on map
if loc:
    st.session_state["latitude"] = loc['coords']['latitude']
    st.session_state["longitude"] = loc['coords']['longitude']

live_location = update_location()
folium.Marker(location=live_location, popup="You are here!",
              icon=folium.Icon(color="red")).add_to(m)

# Write Coords
st.write(
    f"Live Latitude: {st.session_state['latitude']}, Live Longitude: {st.session_state['longitude']}")

# Display map
st_data = st_folium(m, width=700, height=500)

# click on markers for updates
if "marker_content" in st.session_state:
    st.write("Clicked Marker Content:")
    st.write(st.session_state["marker_content"])


# refresh location
if st.button("Refresh Location"):
    loc = get_geolocation()
    if loc:
        st.session_state["latitude"] = loc['coords']['latitude']
        st.session_state["longitude"] = loc['coords']['longitude']
    st.experimental_rerun

# Input stop id manually for developement
stop_ids = bus_stops['stop_id']
entered_stop_id = st.text_input("Enter a stop ID")
entered_stop_id = entered_stop_id.replace(',', '')
# convert to int
try:
    entered_stop_id = int(entered_stop_id)
except ValueError:
    st.error("The entered stop ID is not a valid integer.")
stop_ids = stop_ids.astype(int)
if entered_stop_id:
    if entered_stop_id in stop_ids.values:
        st.write(
            f"Accessing: {bus_stops.loc[bus_stops['stop_id'] == entered_stop_id, 'stop_name'].values[0]} stop")
    else:
        st.write(
            "The entered stop ID does not match any stops in the selected bus line.")

# update_map as session state
if "update_map" not in st.session_state:
    st.session_state.update_map = False
if entered_stop_id:
    st.session_state.update_map = True
else:
    st.session_state.update_map = False


if st.session_state.update_map:

    if entered_stop_id:
        if live_location:
            if st.button("Update Stop to Your Location"):
                # Update the selected bus stop location to the user's live location
                stop_data_service = update_coordinates(
                    stop_data_service, entered_stop_id, live_location[0], live_location[1])

                # Store updates
                update_field('stops', ['stop_lat', 'stop_lon'], {
                    'stop_lat': live_location[0],
                    'stop_lon': live_location[1]
                })

                st.success("Bus stop location updated to your live location.")
        else:
            st.warning("Live location not available.")

# Ensure the updates and update_log tables exist
ensure_tables_exist()

# Automatically upload updates to Supabase table every 2 minutes or with save updates button
if st.button("Save Updates"):
    propagate_updates()

st_autoupdate = st.checkbox("Automatically Save Updates Every 2 Minutes")

if st_autoupdate:
    st_autoupdate_interval = 120  # 2 minutes in seconds

    import time
    from threading import Timer

    def auto_save():
        propagate_updates()
        Timer(st_autoupdate_interval, auto_save).start()

    auto_save()

# Ensure the updates and update_log tables exist


def ensure_tables_exist():
    query_updates = st.session_state['client'].sql.raw(
        'CREATE TABLE IF NOT EXISTS updates (id SERIAL PRIMARY KEY, user_id INTEGER, update TEXT);')
    query_logs = st.session_state['client'].sql.raw(
        'CREATE TABLE IF NOT EXISTS update_log (id SERIAL PRIMARY KEY, user_id INTEGER, log TEXT);')


ensure_tables_exist()

# Pull the current user from the client session state attribute name
current_user = st.session_state["name"]

# Create a DataFrame of updates
updates = pd.DataFrame({
    'user_id': [current_user],
    'update': ['Your update text here']
})

# Push the updates to the updates table in the Supabase client
response = st.session_state['client'].table(
    'updates').insert(updates.to_dict(orient='records'))
