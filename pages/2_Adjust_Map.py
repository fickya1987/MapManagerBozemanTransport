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

#initialize location session state with fill in coords
if "latitude" not in st.session_state:
    st.session_state["latitude"] = bozeman_coords[0]
if "longitude" not in st.session_state:
    st.session_state["longitude"] = bozeman_coords[1]

def update_location ():
    return [st.session_state["latitude"], st.session_state["longitude"]]
    
# Title
st.title("Live Location Map Updates")

if st.button("Upload Data (previous page)"):
    st.switch_page("pages/1_Upload_Data.py")

        ### Build map and put Bus stops on viewer ###

# Initialize a folium map
m = folium.Map(location=bozeman_coords, zoom_start=14, tiles='cartodbpositron')


        ### Modify Marker template to record clicks

#add click event
click_template = """
{% macro script(this, kwargs) %}
    var {{ this.get_name() }} = L.marker(
        {{ this.location|tojson }},
        {{ this.options|tojson }}
    ).addTo({{ this._parent.get_name() }});
    {%- if this.popup %}
    {{ this.get_name() }}.bindPopup({{ this.popup }});
    {{ this.get_name() }}.on('click', function() {
        var content = this.getPopup().getContent();
        var event = new CustomEvent('markerClick', { detail: content });
        document.dispatchEvent(event);
    });
    {%- endif %}
    {%- if this.tooltip %}{{ this.get_name() }}.bindTooltip({{ this.tooltip }});{%- endif %}
{% endmacro %}
"""

#Default marker template
default_template = """
{% macro script(this, kwargs) %}
    var {{ this.get_name() }} = L.marker(
        {{ this.location|tojson }},
        {{ this.options|tojson }}
    ).addTo({{ this._parent.get_name() }});
    {%- if this.popup %}{{ this.get_name() }}.bindPopup({{ this.popup }});{%- endif %}
    {%- if this.tooltip %}{{ this.get_name() }}.bindTooltip({{ this.tooltip }});{%- endif %}
{% endmacro %}
"""
Marker._template = Template(click_template)

# js for click event handling
click_js = """
<script>
document.addEventListener('markerClick', function(event) {
    const content = event.detail;
    fetch('/_stcore_/update_session', {
        method: 'POST',
        body: JSON.stringify({marker_content: content}),
        headers: new Headers({'Content-Type': 'application/json'})
    }).then(response => response.json()).then(data => {
        window.location.reload();
    });
});
</script>
"""
st.components.v1.html(click_js, height=0)

stop_data_service = st.session_state["processed_data"]["stop_data_service"] #pull processed data from session state
bus_lines = organize_by_bus_line(stop_data_service) #organize data by bus line
selected_bus_line = st.selectbox("Select Bus Line", options=bus_lines.keys()) #user select bus line to view

# Add bus stops to the map
if selected_bus_line in bus_lines:
    bus_stops = bus_lines[selected_bus_line]
    unique_stops = bus_stops[['stop_lat', 'stop_lon', 'stop_id', 'stop_name', 'interpolated_time']].drop_duplicates()
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
folium.Marker(location = live_location, popup="You are here!", icon=folium.Icon(color="red")).add_to(m)

#Write Coords
st.write(f"Live Latitude: {st.session_state['latitude']}, Live Longitude: {st.session_state['longitude']}")

# Display map
st_data = st_folium(m, width=700, height=500)

#click on markers for updates
if "marker_content" in st.session_state:
    st.write("Clicked Marker Content:")
    st.write(st.session_state["marker_content"])

#refresh location
if st.button("Refresh Location"):
    loc = get_geolocation()
    if loc:
        st.session_state["latitude"] = loc['coords']['latitude']
        st.session_state["longitude"] = loc['coords']['longitude']
    st.experimental_rerun

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