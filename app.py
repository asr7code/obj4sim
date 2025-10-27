import streamlit as st
import streamlit.components.v1 as components
import time
from datetime import datetime

# -----------------------
# PAGE CONFIGURATION
# -----------------------
st.set_page_config(page_title="ATOA Simulation", layout="wide")
st.title("🚨 AI-Based Advanced Traffic Optimizer & Assistant (ATOA)")
st.subheader("Scripted Demo: Chain-Reaction Prevention")

# -----------------------
# SIDEBAR CONTROLS
# -----------------------
st.sidebar.header("Simulation Controls")
fog_level = st.sidebar.slider("Fog Level (Reduces Visibility)", 0, 90, 80, help="High fog = low visibility. Drivers can't see far.")
run_button = st.sidebar.button("▶ Start Simulation")
reset_button = st.sidebar.button("■ Reset Simulation")

# -----------------------
# SIMULATION CONSTANTS
# -----------------------
ROAD_LENGTH = 100
NORMAL_SPEED = 1  # <--- SET TO 1 FOR SLOW SPEED
BRAKING_SPEED = 0.5 # <--- EVEN SLOWER
VISIBILITY_DISTANCE = 50 * (1 - fog_level / 100.0)
BRAKING_DISTANCE = 15 

# --- SCRIPTED EVENTS ---
CAR_B_START_TIME = 20  # Car B starts when sim time = 20
CAR_C_START_TIME = 35  # Car C starts when sim time = 35
CAR_D_START_TIME = 50  # Car D starts when sim time = 50
CRASH_POINT = 70       # Car B will crash at x=70
CRASH_TIME = 70        # Car B will crash when sim time = 70

# -----------------------
# HELPER FUNCTIONS
# -----------------------

def get_time():
    """Helper to get a simple timestamp for the log."""
    return datetime.now().strftime("%H:%M:%S")

def add_log_entry(log, message, voice_queue=None, speak=False):
    """Adds to log (for voice logic) but log is not displayed."""
    entry = f"[{get_time()}] {message}"
    if not log or log[0] != entry:
        log.insert(0, entry)
        if speak and voice_queue is not None:
            voice_queue.append(message)

def initialize_cars():
    """Creates a list of car dictionaries."""
    cars = {
        'A': {'id': 'A', 'x': -10, 'speed': 0, 'status': 'Waiting', 'alert_message': ''},
        'B': {'id': 'B', 'x': -10, 'speed': 0, 'status': 'Waiting', 'alert_message': ''},
        'C': {'id': 'C', 'x': -10, 'speed': 0, 'status': 'Waiting', 'alert_message': ''},
        'D': {'id': 'D', 'x': -10, 'speed': 0, 'status': 'Waiting', 'alert_message': ''}
    }
    return cars

def update_simulation_logic(cars, sim_time, accident_info, log, voice_queue):
    """Updates the logic for ALL cars based on the scripted time."""
    
    # --- 1. SCRIPTED CAR STARTS ---
    if sim_time == 1:
        cars['A']['status'] = 'Normal'
        cars['A']['speed'] = NORMAL_SPEED
        add_log_entry(log, "Car A is on the road.", voice_queue, speak=True)
    if sim_time == CAR_B_START_TIME:
        cars['B']['status'] = 'Normal'
        cars['B']['speed'] = NORMAL_SPEED
        add_log_entry(log, "Car B is on the road.", voice_queue, speak=True)
    if sim_time == CAR_C_START_TIME:
        cars['C']['status'] = 'Normal'
        cars['C']['speed'] = NORMAL_SPEED
        add_log_entry(log, "Car C is on the road.")
    if sim_time == CAR_D_START_TIME:
        cars['D']['status'] = 'Normal'
        cars['D']['speed'] = NORMAL_SPEED
        add_log_entry(log, "Car D is on the road.")

    # --- 2. SCRIPTED CRASH ---
    if sim_time == CRASH_TIME:
        cars['B']['status'] = 'Crashed'
        cars['B']['speed'] = 0
        cars['B']['x'] = CRASH_POINT # Pin to exact spot
        accident_info = {'id': 'B', 'x': CRASH_POINT}
        add_log_entry(log, "CRITICAL: Car B has crashed! Broadcasting ATOA alert!", voice_queue, speak=True)
    
    # --- 3. UPDATE EACH CAR'S LOGIC ---
    for car_id in ['A', 'B', 'C', 'D']:
        car = cars[car_id]
        if car['status'] == 'Waiting' or car['status'] == 'Finished' or car['status'] == 'Crashed':
            continue # Don't move
            
        old_status = car['status']

        # --- ATOA LOGIC ---
        if accident_info and car['status'] == 'Normal' and car['id'] != 'B':
            car['status'] = 'Braking (Alert)'
            car['alert_message'] = "🚨 ATOA Alert!"
            add_log_entry(log, f"Car {car_id}: Received broadcast! Accident ahead. Braking.", voice_queue, speak=True)

        # --- FIND CAR IN FRONT ---
        # This is complex in a staggered start, so we simplify:
        # Cars C and D only care about the ACCIDENT. Car B only cares about A.
        car_in_front = None
        if car_id == 'B': car_in_front = cars['A']
        if car_id == 'C': car_in_front = cars['B']
        if car_id == 'D': car_in_front = cars['C']

        distance = 999
        if car_in_front and car_in_front['x'] > 0: # Check if car in front is on the road
            distance = car_in_front['x'] - car['x']

        # --- VISUAL & SPEED LOGIC ---
        if car['status'].startswith('Braking'):
            car['speed'] = BRAKING_SPEED
            # Check if we are at the crash site
            if accident_info and car['x'] >= (accident_info['x'] - BRAKING_DISTANCE - 5):
                car['status'] = 'Stopped'
                car['alert_message'] = "Stopped Safely."
        
        elif car['status'] == 'Normal':
            car['speed'] = NORMAL_SPEED
            # Simple follow logic
            if distance < (BRAKING_DISTANCE + 10):
                car['speed'] = BRAKING_SPEED

        # Log status changes
        if car['status'] != old_status and car['status'] == 'Stopped':
            add_log_entry(log, f"Car {car_id}: Stopped safely behind the accident.")

        # --- Move the car ---
        if car['status'] != 'Stopped':
            car['x'] += car['speed']

        # --- Check if finished ---
        if car['x'] >= ROAD_LENGTH:
            car['status'] = 'Finished'
            car['x'] = ROAD_LENGTH
            car['speed'] = 0
            if car_id == 'A':
                add_log_entry(log, "Car A finished safely.")

    return accident_info


def render_drivers_view(driver_car, all_cars):
    """Renders the road from the driver's perspective, including fog."""
    view_length = 60 
    road = ["-"] * view_length
    
    if driver_car['status'] == 'Waiting':
        return "[Waiting to start...]"
    if driver_car['status'] == 'Finished':
        return "[Finished]"
    
    # Place the driver's car
    road[0] = "🚘"
    if driver_car['status'] == 'Crashed': road[0] = "💥"
    if driver_car['status'] == 'Stopped': road[0] = "🛑"
    if driver_car['status'] == 'Braking (Alert)': road[0] = "B" # 'B' for ATOA Braking

    occupied_positions = {}
    for car in all_cars.values():
        if car['id'] == driver_car['id'] or car['x'] < driver_car['x']:
            continue # Skip self or cars behind
            
        distance = car['x'] - driver_car['x']
            
        if 0 < distance < view_length:
            distance_int = int(distance)
            symbol = "?"
            
            if distance <= VISIBILITY_DISTANCE:
                if car['status'] == 'Crashed': symbol = "💥"
                elif car['status'] == 'Stopped': symbol = "🛑"
                elif car['status'] == 'Braking (Alert)': symbol = "B"
                else: symbol = "🚘"
            else:
                symbol = "▒" # Fog
            
            if distance_int not in occupied_positions or occupied_positions[distance_int] == "▒":
                occupied_positions[distance_int] = symbol

    for pos, symbol in occupied_positions.items():
        if 0 <= pos < len(road):
            road[pos] = symbol
            
    return "".join(road)

def speak_alerts(voice_queue):
    """Generates JS to speak all queued alerts."""
    if not voice_queue:
        return ""
    script = "<script>"
    for alert_text in voice_queue:
        alert_text = alert_text.replace("'", "").replace('"', "")
        script += f"var msg = new SpeechSynthesisUtterance('{alert_text}'); window.speechSynthesis.speak(msg);"
    script += "</script>"
    return script

# -----------------------
# INITIALIZE SESSION STATE
# -----------------------
if 'simulation_running' not in st.session_state:
    st.session_state.simulation_running = False
    st.session_state.sim_time = 0
    st.session_state.cars = initialize_cars()
    st.session_state.accident_info = None
    st.session_state.alert_log = []

if run_button:
    st.session_state.simulation_running = True
    st.session_state.sim_time = 0
    st.session_state.cars = initialize_cars()
    st.session_state.accident_info = None
    st.session_state.alert_log = [f"[{get_time()}] Simulation Started."]
    st.rerun() # Start the loop

if reset_button:
    st.session_state.simulation_running = False
    st.session_state.sim_time = 0
    st.session_state.cars = initialize_cars()
    st.session_state.accident_info = None
    st.session_state.alert_log = []
    st.rerun() 

# -----------------------
# MAIN SIMULATION RENDER
# -----------------------
if st.session_state.simulation_running:
    
    # --- Placeholders for UI elements ---
    st.markdown(f"**Fog Visibility:** `{VISIBILITY_DISTANCE:.1f} units` | **Simulation Time:** `{st.session_state.sim_time}`")
    
    colA, colB = st.columns(2)
    with colA:
        st.subheader("Car A")
        dashA_placeholder = st.empty()
        st.subheader("Car B")
        dashB_placeholder = st.empty()
    with colB:
        st.subheader("Car C")
        dashC_placeholder = st.empty()
        st.subheader("Car D")
        dashD_placeholder = st.empty()
        
    # This placeholder is the fix for the DeltaGenerator error
    voice_placeholder = st.empty()
    
    # --- 1. Clear voice queue ---
    st.session_state.voice_queue = []

    # --- 2. Update logic ---
    st.session_state.accident_info = update_simulation_logic(
        st.session_state.cars, 
        st.session_state.sim_time, 
        st.session_state.accident_info, 
        st.session_state.alert_log, 
        st.session_state.voice_queue
    )

    # --- 3. Render the simulation ---
    dashA_placeholder.code(f"View: {render_drivers_view(st.session_state.cars['A'], st.session_state.cars)}", language="text")
    dashB_placeholder.code(f"View: {render_drivers_view(st.session_state.cars['B'], st.session_state.cars)}", language="text")
    dashC_placeholder.code(f"View: {render_drivers_view(st.session_state.cars['C'], st.session_state.cars)}", language="text")
    dashD_placeholder.code(f"View: {render_drivers_view(st.session_state.cars['D'], st.session_state.cars)}", language="text")

    # --- 4. Process Voice Alerts (Hidden) ---
    voice_html = speak_alerts(st.session_state.voice_queue)
    voice_placeholder.empty() 
    voice_placeholder.write(components.html(voice_html, height=0))

    # --- 5. Increment time and rerun ---
    st.session_state.sim_time += 1

    # Check for end condition
    if all(c['status'] in ['Finished', 'Stopped', 'Crashed'] for c in st.session_state.cars.values()):
        st.session_state.simulation_running = False
        st.success("Simulation Demo Finished.")
        if st.session_state.cars['C']['status'] == 'Stopped' and st.session_state.cars['D']['status'] == 'Stopped':
             st.success("Proof of Concept: Cars C and D received the ATOA alert and stopped safely!")
        st.balloons()
    else:
        time.sleep(0.4) # Control the simulation speed
        st.rerun()

else:
    st.info("Press 'Start Simulation' in the sidebar to begin.")
