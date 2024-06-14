import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium
from streamlit.components.v1 import html

@st.cache_data
def organize_by_bus_line(df):
    bus_lines = {}
    for line in df['route_long_name'].unique():
            if line not in bus_lines:
                bus_lines[line] = []
            bus_lines[line].append(df[df['route_long_name'] == line])
    return {line: pd.concat(dfs) for line, dfs in bus_lines.items()}

def update_coordinates(df, stop_id, new_lat, new_lon):
    df.loc[df['stop_id'] == stop_id, ['latitude', 'longitude']] = new_lat, new_lon
    return df

def get_live_location():
    js_code = """
    <script>
    navigator.geolocation.getCurrentPosition(
        (position) => {
            const latitude = position.coords.latitude;
            const longitude = position.coords.longitude;
            const accuracy = position.coords.accuracy;
            const coordinates = {
                "latitude": latitude.toFixed(5),
                "longitude": longitude.toFixed(5),
                "accuracy": accuracy.toFixed(2)
            };
            document.dispatchEvent(new CustomEvent('locationUpdate', {detail: coordinates}));
        },
        (error) => {
            console.error("Error Code = " + error.code + " - " + error.message);
        }
    );
    </script>
    """
    html(js_code)

def location_update():
    latitude = st.session_state.get("latitude", 0)
    longitude = st.session_state.get("longitude", 0)
    return latitude, longitude

def init_location():
    if "latitude" not in st.session_state or "longitude" not in st.session_state:
        get_live_location()
        # Provide initial default values if not set
        st.session_state["latitude"] = 0.0
        st.session_state["longitude"] = 0.0

# Add JavaScript to listen for the custom event and update session state
html("""
<script>
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
</script>
""")