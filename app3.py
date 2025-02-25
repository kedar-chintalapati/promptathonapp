import streamlit as st
import requests
import pandas as pd
import altair as alt

# -----------------------------------------------------
# Configuration & Style
# -----------------------------------------------------
st.set_page_config(
    page_title="Rubber Duck High-Elevation Simulator",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS to hide default Streamlit elements, add a gradient background, and style widgets
CUSTOM_CSS = """
<style>
/* Hide Streamlit header, footer, and toolbar (Share, etc.) */
#MainMenu, header, footer, [data-testid="stToolbar"] {
    visibility: hidden;
    height: 0;
    display: none;
}

/* Hide the "Manage app" button in bottom right (Streamlit Cloud) */
.viewerBadge_container__1QSob, .viewerBadge_link__1S137 {
    visibility: hidden;
    display: none;
}

/* Gradient background for the entire page */
html, body, [class*="css"]  {
    background: linear-gradient(180deg, #141E30 0%, #243B55 100%) !important;
    color: #FFFFFF !important;
    font-family: "Helvetica Neue", sans-serif;
}

/* Streamlit main block container */
.block-container {
    padding-top: 2rem !important;
    padding-bottom: 2rem !important;
}

/* Sidebar background */
[data-testid="stSidebar"] {
    background-color: #0f0f0f !important;
}

/* Input fields, text areas, select boxes */
textarea, input, select, .css-1msw3jc {
    background-color: #1f1f1f !important;
    color: #ffffff !important;
    border: 1px solid #444444 !important;
}

/* Slider styling */
.css-1dp5vir {
    color: #ffffff !important;
}

/* Buttons */
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

/* DataFrame styling */
[data-testid="stDataFrame"] {
    background-color: #222222 !important;
    color: #ffffff !important;
    border: 1px solid #444444 !important;
}

/* Expander styling */
.streamlit-expanderHeader {
    font-weight: bold !important;
    background-color: #1f1f1f !important;
    color: #ffffff !important;
    border: 1px solid #444444 !important;
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# -----------------------------------------------------
# Caching External API Calls
# -----------------------------------------------------
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
        st.error(f"Error fetching elevation data: {e}")
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
        st.error(f"Error fetching weather data: {e}")
    return None

# -----------------------------------------------------
# Simulation Logic
# -----------------------------------------------------
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

# Default transport modes with baseline parameters and cost models
TRANSPORT_MODES = {
    "Helium Balloon": {
        "base_cost": 10,
        "cost_per_gram": 0.02,
        "cost_per_km": 0.2,
        "efficiency": 1.1,
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

# Initialize session state for data storage across steps
if "base_elev" not in st.session_state:
    st.session_state.base_elev = None
if "weather_data" not in st.session_state:
    st.session_state.weather_data = None

# -----------------------------------------------------
# App Layout (Step-by-Step with Expanders)
# -----------------------------------------------------
def main():
    st.title("Rubber Duck High-Elevation Simulator")
    st.markdown("""
    Welcome to this step-by-step tool for planning how to get a rubber duck to a high elevation!
    Follow each step below to configure your parameters, fetch real-world data, and simulate results.
    """)

    # ---------------- Step 1: Provide Location ----------------
    with st.expander("Step 1: Provide Your Location", expanded=True):
        st.write("Enter a latitude and longitude for the place where you want to start your journey.")
        col1, col2 = st.columns(2)
        with col1:
            lat = st.number_input("Latitude", min_value=-90.0, max_value=90.0, value=40.7128, step=0.0001)
        with col2:
            lon = st.number_input("Longitude", min_value=-180.0, max_value=180.0, value=-74.0060, step=0.0001)

        if st.button("Fetch Elevation & Weather", key="fetch_data"):
            with st.spinner("Fetching external data..."):
                elev = fetch_base_elevation(lat, lon)
                weather = fetch_weather(lat, lon)
            if elev is not None:
                st.success(f"Base Elevation Fetched: {elev:.1f} m")
                st.session_state.base_elev = elev
            else:
                st.error("Failed to fetch elevation data.")
            if weather is not None:
                st.success(f"Weather Fetched: {weather.get('temperature', 'N/A')}°C, "
                           f"Wind {weather.get('wind_speed', 'N/A')} km/h")
                st.session_state.weather_data = weather
            else:
                st.error("Failed to fetch weather data.")

    # ---------------- Step 2: Overrides ----------------
    with st.expander("Step 2: Override or Confirm Fetched Data", expanded=False):
        st.write("""
        If the external data is unavailable or you want to use your own values, you can override them here.
        Otherwise, just confirm the fetched data.
        """)
        override_base_elev = st.checkbox("Override Base Elevation?", value=False)
        manual_base_elev = st.number_input("Manual Base Elevation (m)", value=0.0, step=1.0)
        override_weather = st.checkbox("Override Weather Factor?", value=False)
        manual_weather_factor = st.slider("Manual Weather Factor", 0.5, 1.5, 1.0, step=0.05)

    # ---------------- Step 3: Rubber Duck Mass ----------------
    with st.expander("Step 3: Set Rubber Duck Mass", expanded=False):
        st.write("Specify the mass of your rubber duck in grams (default is 10 g).")
        duck_mass = st.number_input("Rubber Duck Mass (grams)", min_value=1.0, value=10.0, step=1.0)

    # ---------------- Step 4: Configure Lift Methods ----------------
    with st.expander("Step 4: Configure Lift Methods", expanded=False):
        st.write("""
        Adjust the cost and efficiency parameters for each available lift method.
        You can add or remove methods by editing the code or adjusting these parameters.
        """)
        transport_params = {}
        for mode, params in TRANSPORT_MODES.items():
            st.write(f"**{mode}**")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                base_cost = st.number_input(
                    f"{mode} - Base Cost",
                    min_value=0.0,
                    value=float(params["base_cost"]),
                    step=1.0
                )
            with col2:
                cost_per_gram = st.number_input(
                    f"{mode} - Cost/gram",
                    min_value=0.0,
                    value=float(params["cost_per_gram"]),
                    step=0.01
                )
            with col3:
                cost_per_km = st.number_input(
                    f"{mode} - Cost/km",
                    min_value=0.0,
                    value=float(params["cost_per_km"]),
                    step=0.01
                )
            with col4:
                efficiency = st.slider(
                    f"{mode} - Efficiency",
                    min_value=0.5, max_value=2.0,
                    value=float(params["efficiency"]),
                    step=0.05
                )
            transport_params[mode] = {
                "base_cost": base_cost,
                "cost_per_gram": cost_per_gram,
                "cost_per_km": cost_per_km,
                "efficiency": efficiency,
            }
        st.write("All set? Great! Move on to the next step.")

    # ---------------- Step 5: Choose Target Altitude ----------------
    with st.expander("Step 5: Choose Target Altitude Above Base", expanded=False):
        st.write("""
        Select how many kilometers above the base elevation you aim to reach.
        """)
        altitude_km = st.slider("Target Altitude (km above base)", 0.0, 30.0, 1.0, step=0.1)

    # ---------------- Step 6: Run Simulation ----------------
    with st.expander("Step 6: Run the Simulation & View Results", expanded=False):
        st.write("Click the button below to compute final elevation and costs for each method.")
        if st.button("Run Simulation", key="run_sim"):
            # Determine base_elev
            if (st.session_state.base_elev is None) and not override_base_elev:
                st.error("No base elevation data. Please fetch or override.")
                return
            final_base_elev = (
                st.session_state.base_elev
                if (st.session_state.base_elev is not None and not override_base_elev)
                else manual_base_elev
            )

            # Determine weather factor
            if (st.session_state.weather_data is None) and not override_weather:
                st.error("No weather data. Please fetch or override.")
                return
            if st.session_state.weather_data is not None and not override_weather:
                wind_speed = st.session_state.weather_data.get("wind_speed", 0)
                computed_weather_factor = compute_weather_factor(wind_speed)
            else:
                computed_weather_factor = manual_weather_factor

            # Perform simulation
            results = []
            for mode, params in transport_params.items():
                eff = params["efficiency"]
                bc = params["base_cost"]
                cpg = params["cost_per_gram"]
                cpk = params["cost_per_km"]

                total_elev = simulate_elevation(
                    base_elev=final_base_elev,
                    altitude_km=altitude_km,
                    efficiency=eff,
                    weather_factor=computed_weather_factor
                )

                total_cost = estimate_cost(
                    base_cost=bc,
                    cost_per_gram=cpg,
                    cost_per_km=cpk,
                    mass_g=duck_mass,
                    altitude_km=altitude_km
                )

                results.append({
                    "Mode": mode,
                    "Final Elevation (m)": round(total_elev, 2),
                    "Estimated Cost (USD)": round(total_cost, 2),
                })

            df_results = pd.DataFrame(results)

            st.success("Simulation Complete! See results below.")
            colA, colB = st.columns(2)
            with colA:
                st.markdown(f"**Base Elevation:** {final_base_elev:.2f} m")
                st.markdown(f"**Target Altitude Above Base:** {altitude_km} km")
                st.markdown(f"**Weather Factor:** {computed_weather_factor}")
                st.markdown(f"**Rubber Duck Mass:** {duck_mass} g")

            if st.session_state.weather_data is not None and not override_weather:
                with colB:
                    temp = st.session_state.weather_data.get('temperature', 'N/A')
                    ws = st.session_state.weather_data.get('wind_speed', 'N/A')
                    st.markdown(f"**Temperature:** {temp} °C")
                    st.markdown(f"**Wind Speed:** {ws} km/h")

            st.dataframe(df_results.set_index("Mode"))

            # Charts
            st.subheader("Elevation & Cost Comparison")
            chart_col1, chart_col2 = st.columns(2)
            with chart_col1:
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

            with chart_col2:
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

            st.info("You can adjust any step above and re-run the simulation to see new results.")

if __name__ == "__main__":
    main()
