import streamlit as st
import requests
import pandas as pd
import altair as alt

# --- Constants & Configurations ---
ST_TITLE = "Rubber Duck Elevation Simulator"
ST_DESCRIPTION = """
Simulate strategies to get a rubber duck to the highest possible elevation given a budget scenario.
This app uses real weather data (from Open-Meteo) and elevation data (from Open-Elevation) to help you explore different transportation options.
"""
# Transportation options with efficiency multipliers
TRANSPORT_MODES = [
    {"name": "Helium Balloon", "efficiency": 1.1},
    {"name": "Drone", "efficiency": 1.3},
    {"name": "Hot Air Balloon", "efficiency": 1.5},
    {"name": "Catapult", "efficiency": 1.05},
]

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

def simulate_elevation(base_elev: float, budget: float, efficiency: float, weather_factor: float):
    """
    Compute additional elevation based on the formula:
        additional = (budget/50) * efficiency * weather_factor * 50
    and add it to the base elevation.
    """
    additional = (budget / 50) * efficiency * weather_factor * 50
    return base_elev + additional

# --- Streamlit App Layout ---
def main():
    st.set_page_config(page_title=ST_TITLE, layout="wide")
    st.title(ST_TITLE)
    st.markdown(ST_DESCRIPTION)

    # Sidebar: Input Parameters
    st.sidebar.header("Simulation Settings")

    # Budget scenario selection
    budget_option = st.sidebar.radio("Select Budget Scenario", options=["$50", "$500"])
    budget = 50 if budget_option == "$50" else 500

    # Coordinates input
    st.sidebar.subheader("Location Settings")
    lat = st.sidebar.number_input("Latitude", min_value=-90.0, max_value=90.0, value=40.7128, step=0.0001)
    lon = st.sidebar.number_input("Longitude", min_value=-180.0, max_value=180.0, value=-74.0060, step=0.0001)
    
    # Buttons to fetch external data
    if st.sidebar.button("Fetch Base Elevation"):
        with st.spinner("Fetching elevation..."):
            base_elev = fetch_base_elevation(lat, lon)
            if base_elev is not None:
                st.sidebar.success(f"Base Elevation: {base_elev:.1f} m")
            else:
                st.sidebar.error("Could not fetch elevation.")

    if st.sidebar.button("Fetch Current Weather"):
        with st.spinner("Fetching weather data..."):
            weather = fetch_weather(lat, lon)
            if weather is not None:
                wind_speed = weather.get("wind_speed", 0)
                temperature = weather.get("temperature", 0)
                st.sidebar.success(f"Temperature: {temperature}°C, Wind: {wind_speed} km/h")
            else:
                st.sidebar.error("Could not fetch weather data.")

    st.sidebar.markdown("---")
    st.sidebar.markdown("Adjust additional simulation parameters below if needed.")

    # Optional: Allow user to adjust multipliers manually if desired
    manual_weather_factor = st.sidebar.slider("Override Weather Factor", 0.5, 1.5, 1.0, step=0.05)
    use_manual_weather = st.sidebar.checkbox("Use manual weather factor", value=False)

    # Main simulation execution
    st.header("Run Simulation")
    if st.button("Run Simulation"):
        # Fetch external data first
        with st.spinner("Fetching external data..."):
            base_elev = fetch_base_elevation(lat, lon)
            weather = fetch_weather(lat, lon)

        if base_elev is None or weather is None:
            st.error("Missing external data. Please try fetching again.")
            return

        # Compute weather factor from wind speed if not using manual override
        wind_speed = weather.get("wind_speed", 0)
        weather_factor = compute_weather_factor(wind_speed)
        if use_manual_weather:
            weather_factor = manual_weather_factor

        # Prepare simulation results for each transportation mode
        results = []
        for mode in TRANSPORT_MODES:
            mode_name = mode["name"]
            efficiency = mode["efficiency"]
            total_elevation = simulate_elevation(base_elev, budget, efficiency, weather_factor)
            results.append({
                "Mode": mode_name,
                "Efficiency": efficiency,
                "Simulated Total Elevation (m)": round(total_elevation, 1)
            })

        # Convert to DataFrame for display and visualization
        df = pd.DataFrame(results)
        
        # Display the simulation summary
        st.subheader("Simulation Parameters")
        st.write(f"**Budget Scenario:** {budget_option}")
        st.write(f"**Location:** Latitude {lat}, Longitude {lon}")
        st.write(f"**Base Elevation:** {base_elev:.1f} m")
        st.write(f"**Weather:** Temperature {weather.get('temperature', 'N/A')}°C, Wind Speed {wind_speed} km/h")
        st.write(f"**Weather Factor:** {weather_factor}")

        st.subheader("Simulation Results")
        st.dataframe(df.set_index("Mode"))

        # Visualization: Bar chart comparing simulated total elevation
        chart = alt.Chart(df).mark_bar().encode(
            x=alt.X("Mode:N", title="Transportation Mode"),
            y=alt.Y("Simulated Total Elevation (m):Q", title="Total Elevation (m)"),
            color=alt.Color("Mode:N", legend=None),
            tooltip=["Mode", "Efficiency", "Simulated Total Elevation (m)"]
        ).properties(
            width=600,
            height=400,
            title="Simulated Total Elevation by Transportation Mode"
        )
        st.altair_chart(chart, use_container_width=True)

        st.success("Simulation complete! Adjust parameters and re-run for different outcomes.")

if __name__ == "__main__":
    main()
