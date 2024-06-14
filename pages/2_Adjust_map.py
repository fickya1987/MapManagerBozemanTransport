import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from streamlit.components.v1 import html
from components.menu import menu_with_redirect
from components.map import *
from components.databasefuncs import ensure_tables_exist, update_field, propagate_updates

# Initialize user session and verify login
menu_with_redirect()

# Verify the user's role
if not st.session_state.get("authentication_status", False):
    st.warning("You do not have permission to view this page.")
    st.stop()

# Title of the app
st.title("Live Location updates")

# Center the map on Bozeman, Montana
bozeman_coords = [45.6770, -111.0429]

#pull processed data from session state
stop_data_service = st.session_state["processed_data"]["stop_data_service"]

init_location()
html("""<script>
document.addEventListener('locationUpdate', function(event) {
    const coordinates = event.detail;
    fetch('/_stcore_/update_session', {
        method: 'POST',
        body: JSON.stringify(coordinates),
        headers: new Headers({'Content-Type': 'application/json'})
    }).then(response => response.json()).then(data => {
        window.location.reload();
    });
});
</script>""")

live_lat = st.session_state["latitude"]
live_long = st.session_state["longitude"]
live_location = [float(live_lat), float(live_long)] if live_lat and live_long else None

# Organize stops by bus line
bus_lines = organize_by_bus_line(stop_data_service)
selected_bus_line = st.selectbox("Select Bus Line", options=bus_lines.keys())

# Initialize a folium map
m = folium.Map(location=bozeman_coords, zoom_start=12, tiles='cartodbpositron')

# Add bus stops to the map
bus_stops = bus_lines[selected_bus_line]
unique_stops = bus_stops[['stop_lat', 'stop_lon', 'stop_id']].drop_duplicates()
for _, stop in unique_stops.iterrows():
    folium.Marker(location=[stop['stop_lat'], stop['stop_lon']], popup=stop['stop_id']).add_to(m)

#put live location on map
if live_location:
    folium.Marker(location=live_location, popup="You are here!", icon=folium.Icon(color="red")).add_to(m)

# Display map
st_data = st_folium(m, width=700, height=500)

#refresh location
if st.button("Refresh Location"):
    get_live_location()

#update_map as session state
update_map = st.radio("Update Map", ["No", "Yes"])
if "update_map" not in st.session_state:
    st.session_state.update_map = False
if update_map == "Yes":
    st.session_state.update_map = True
else:
    st.session_state.update_map = False

'''
if st.session_state.update_map:
    selected_stop_id = st.text_input("Selected Stop ID")
    
    if selected_stop_id:
        if live_location:
            if st.button("Update Stop to Your Location"):
                # Update the selected bus stop location to the user's live location
                stop_data_service = update_coordinates(stop_data_service, selected_stop_id, live_lat, live_long)
                
                # Store updates
                update_field('stops', ['stop_lat', 'stop_lon'], {
                    'stop_lat': live_lat,
                    'stop_lon': live_long
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

'''