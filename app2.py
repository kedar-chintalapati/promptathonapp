import streamlit as st
import requests
import pandas as pd
import altair as alt

# --- Constants & Configurations ---
ST_TITLE = "Rubber Duck High-Elevation Simulator"
ST_DESCRIPTION = """
Explore strategies to get a rubber duck to the highest possible elevation.
This advanced app lets you enter detailed parameters for different lift methods,
fetches real weather & elevation data, and estimates costs and achievable altitudes.
"""

# Default transport modes with baseline parameters and cost models
# (You can add more or adjust these as needed)
TRANSPORT_MODES = {
    "Helium Balloon": {
        "base_cost": 10,          # Base cost in USD
        "cost_per_gram": 0.02,    # Additional cost per gram of payload
        "cost_per_km": 0.2,       # Additional cost per km of altitude
        "efficiency": 1.1,        # Lift efficiency factor
    },
    "Drone": {
        "base_cost": 20,
        "cost_per_gram": 0.05,
        "cost_per_km": 0.15,
        "efficiency": 1.3,
    },
    "Hot Air Balloon": {
        "base_cost": 50,
        "cost_per_gram": 0.01,
        "cost_per_km": 0.1,
        "efficiency": 1.5,
    },
    "Catapult": {
        "base_cost": 5,
        "cost_per_gram": 0.005,
        "cost_per_km": 0.3,
        "efficiency": 1.05,
    },
}

# --- Streamlit configuration ---
# Hide the default Streamlit menu and footer, and set page to wide layout
st.set_page_config(page_title=ST_TITLE, layout="wide", initial_sidebar_state="expanded")

# Inject CSS to remove top bar and footer, and create a dark theme
CUSTOM_CSS = """
<style>
/* Hide Streamlit header and footer */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

/* Make background black and text light */
html, body, [class*="css"]  {
    background-color: #000000 !important;
    color: #FFFFFF !important;
    font-family: "Helvetica Neue", sans-serif;
}

/* Customize input fields, sliders, and buttons */
.css-1cypcdb, .css-1r5f3iu, .css-1e5imcs {
    background-color: #333333 !important;
    color: #FFFFFF !important;
    border: 1px solid #666666 !important;
}

.css-1n76uvr {
    color: #FFFFFF !important;
}

/* Sidebar styling */
.css-1d391kg {
    background-color: #111111 !important;
}

/* Button styling */
.stButton button {
    background: linear-gradient(to right, #614385, #516395) !important;
    color: #FFFFFF !important;
    border: 0px;
    border-radius: 5px;
    padding: 0.6em 1.2em;
    cursor: pointer;
}
.stButton button:hover {
    background: linear-gradient(to right, #7d5fb2, #7d87b2) !important;
}

/* Titles and headers */
h1, h2, h3, h4 {
    color: #ffffff !important;
}

/* DataFrame styling */
[data-testid="stDataFrame"] {
    background-color: #222222 !important;
    border: 1px solid #444444 !important;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# --- Caching API calls to optimize performance ---
@st.cache_data(show_spinner=False)
def fetch_base_elevation(lat: float, lon: float):
    """
    Fetch the elevation at the specified coordinates using the Open-Elevation API.
    """
    url = f"https://api.open-elevation.com/api/v1/lookup?locations={lat},{lon}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("results"):
            elevation = data["results"][0].get("elevation")
            return elevation
    except Exception as e:
        st.error("Error fetching elevation data.")
    return None

@st.cache_data(show_spinner=False)
def fetch_weather(lat: float, lon: float):
    """
    Fetch the current weather at the specified coordinates using the Open-Meteo API.
    Returns a dict with 'temperature', 'wind_speed', etc.
    """
    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
        "&current_weather=true"
    )
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("current_weather"):
            return data["current_weather"]
    except Exception as e:
        st.error("Error fetching weather data.")
    return None

def compute_weather_factor(wind_speed: float):
    """
    Compute a weather factor based on wind speed (in km/h).
    """
    if wind_speed < 10:
        return 1.0
    elif wind_speed < 20:
        return 0.9
    else:
        return 0.8

def simulate_elevation(base_elev: float, altitude_km: float, efficiency: float, weather_factor: float):
    """
    Rough formula to estimate final elevation:
        final = base_elev + altitude_km * 1000 * efficiency * weather_factor
    """
    additional = altitude_km * 1000 * efficiency * weather_factor
    return base_elev + additional

def estimate_cost(base_cost, cost_per_gram, cost_per_km, mass_g, altitude_km):
    """
    Rough cost estimation:
        cost = base_cost + (cost_per_gram * mass_g) + (cost_per_km * altitude_km)
    """
    return base_cost + (cost_per_gram * mass_g) + (cost_per_km * altitude_km)

def main():
    st.title(ST_TITLE)
    st.markdown(ST_DESCRIPTION)

    # Sidebar: Parameter Inputs
    st.sidebar.header("Simulation Settings")

    # Coordinates input
    st.sidebar.subheader("Location Settings")
    lat = st.sidebar.number_input("Latitude", min_value=-90.0, max_value=90.0, value=40.7128, step=0.0001)
    lon = st.sidebar.number_input("Longitude", min_value=-180.0, max_value=180.0, value=-74.0060, step=0.0001)

    # Fetch external data buttons
    if st.sidebar.button("Fetch Elevation & Weather"):
        with st.spinner("Fetching external data..."):
            base_elev = fetch_base_elevation(lat, lon)
            weather_data = fetch_weather(lat, lon)
        if base_elev is not None:
            st.sidebar.success(f"Base Elevation: {base_elev:.1f} m")
        else:
            st.sidebar.error("Failed to fetch elevation.")
        if weather_data is not None:
            wind_speed = weather_data.get("wind_speed", 0)
            temperature = weather_data.get("temperature", 0)
            st.sidebar.success(f"Weather: {temperature}°C, Wind: {wind_speed} km/h")
        else:
            st.sidebar.error("Failed to fetch weather.")
    else:
        base_elev = None
        weather_data = None

    # User can override if they want to proceed without fetching data
    override_base_elev = st.sidebar.checkbox("Override Base Elevation", value=False)
    manual_base_elev = st.sidebar.number_input("Manual Elevation (m)", value=0.0, step=1.0)
    override_weather = st.sidebar.checkbox("Override Weather Factor", value=False)
    manual_weather_factor = st.sidebar.slider("Manual Weather Factor", 0.5, 1.5, 1.0, step=0.05)

    # Duck mass
    st.sidebar.subheader("Rubber Duck Mass")
    duck_mass = st.sidebar.number_input("Mass of Rubber Duck (grams)", min_value=1.0, value=10.0, step=1.0)

    # Display advanced parameters for each transportation method
    st.sidebar.subheader("Lift Methods Configuration")
    transport_params = {}
    for mode, params in TRANSPORT_MODES.items():
        with st.sidebar.expander(mode, expanded=False):
            base_cost = st.number_input(f"{mode} - Base Cost", min_value=0.0, value=float(params["base_cost"]), step=1.0)
            cost_per_gram = st.number_input(f"{mode} - Cost per gram", min_value=0.0, value=float(params["cost_per_gram"]), step=0.001)
            cost_per_km = st.number_input(f"{mode} - Cost per km altitude", min_value=0.0, value=float(params["cost_per_km"]), step=0.01)
            efficiency = st.slider(f"{mode} - Efficiency", min_value=0.5, max_value=2.0, value=float(params["efficiency"]), step=0.05)
            transport_params[mode] = {
                "base_cost": base_cost,
                "cost_per_gram": cost_per_gram,
                "cost_per_km": cost_per_km,
                "efficiency": efficiency,
            }

    # Main page: Altitude input
    st.header("Simulation Input")
    st.write("Configure how high you aim to go and then run the simulation.")

    altitude_km = st.slider("Target Additional Altitude (km above base)", 0.0, 20.0, 1.0, step=0.1)

    # Simulation button
    if st.button("Run Simulation"):
        if (base_elev is None or weather_data is None) and not (override_base_elev and override_weather):
            st.error("Missing external data or overrides. Fetch data or use override options.")
            return

        final_base_elev = base_elev if (base_elev is not None and not override_base_elev) else manual_base_elev
        if weather_data is not None and not override_weather:
            wind_speed = weather_data.get("wind_speed", 0)
            computed_weather_factor = compute_weather_factor(wind_speed)
        else:
            computed_weather_factor = manual_weather_factor

        # Calculate results for each transport mode
        results = []
        for mode, params in transport_params.items():
            # Efficiency & cost parameters
            efficiency = params["efficiency"]
            base_cost = params["base_cost"]
            cost_per_gram = params["cost_per_gram"]
            cost_per_km = params["cost_per_km"]

            # Elevation simulation
            total_elev = simulate_elevation(
                base_elev=final_base_elev,
                altitude_km=altitude_km,
                efficiency=efficiency,
                weather_factor=computed_weather_factor
            )

            # Cost simulation
            total_cost = estimate_cost(
                base_cost=base_cost,
                cost_per_gram=cost_per_gram,
                cost_per_km=cost_per_km,
                mass_g=duck_mass,
                altitude_km=altitude_km
            )

            results.append({
                "Mode": mode,
                "Final Elevation (m)": round(total_elev, 2),
                "Estimated Cost (USD)": round(total_cost, 2),
            })

        df_results = pd.DataFrame(results)

        st.subheader("Simulation Results")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Base Elevation:** {final_base_elev:.2f} m")
            st.write(f"**Target Altitude Above Base:** {altitude_km} km")
            st.write(f"**Weather Factor:** {computed_weather_factor}")
            st.write(f"**Rubber Duck Mass:** {duck_mass} g")

        if weather_data is not None and not override_weather:
            with col2:
                st.write(f"**Temperature:** {weather_data.get('temperature', 'N/A')}°C")
                st.write(f"**Wind Speed:** {weather_data.get('wind_speed', 'N/A')} km/h")

        st.dataframe(df_results.set_index("Mode"))

        # Visualization
        st.subheader("Elevation & Cost Comparison")
        # Create two charts side-by-side
        col3, col4 = st.columns(2)

        with col3:
            st.markdown("**Elevation by Transportation Mode**")
            chart_elev = alt.Chart(df_results).mark_bar().encode(
                x=alt.X("Mode:N", sort=None),
                y=alt.Y("Final Elevation (m):Q"),
                color=alt.Color("Mode:N", legend=None),
                tooltip=["Mode", "Final Elevation (m)"]
            ).properties(
                width="container",
                height=400
            )
            st.altair_chart(chart_elev, use_container_width=True)

        with col4:
            st.markdown("**Cost by Transportation Mode**")
            chart_cost = alt.Chart(df_results).mark_bar().encode(
                x=alt.X("Mode:N", sort=None),
                y=alt.Y("Estimated Cost (USD):Q"),
                color=alt.Color("Mode:N", legend=None),
                tooltip=["Mode", "Estimated Cost (USD)"]
            ).properties(
                width="container",
                height=400
            )
            st.altair_chart(chart_cost, use_container_width=True)

        st.success("Simulation complete! Adjust parameters and re-run for different outcomes.")

if __name__ == "__main__":
    main()
