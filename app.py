import streamlit as st
import streamlit.components.v1 as components
import time
from datetime import datetime
import math

# -----------------------
# PAGE CONFIGURATION
# -----------------------
st.set_page_config(page_title="ATOA Simulation", layout="wide")
st.title("🚨 AI-Based Advanced Traffic Optimizer & Assistant (ATOA)")
st.subheader("Scripted Demo: Blackspot Accident Prevention")

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
NORMAL_SPEED = 1      # Cars move slowly
BRAKING_SPEED = 0.5   # Cars brake even slower
VISIBILITY_DISTANCE = 50 * (1 - fog_level / 100.0)
BRAKING_DISTANCE = 15 

# --- SCRIPTED EVENTS ---
CAR_2_START_TIME = 20  # Car 2 starts when sim time = 20
CAR_3_START_TIME = 35  # Car 3 starts when sim time = 35
CAR_4_START_TIME = 50  # Car 4 starts when sim time = 50
BLACKSPOT_B = 70       # Position of the blackspot
CRASH_TIME = 70        # Car 2 will crash when sim time = 70

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
        '1': {'id': '1', 'x': -10, 'speed': 0, 'status': 'Waiting', 'alert_message': ''},
        '2': {'id': '2', 'x': -10, 'speed': 0, 'status': 'Waiting', 'alert_message': ''},
        '3': {'id': '3', 'x': -10, 'speed': 0, 'status': 'Waiting', 'alert_message': ''},
        '4': {'id': '4', 'x': -10, 'speed': 0, 'status': 'Waiting', 'alert_message': ''}
    }
    return cars

def update_simulation_logic(cars, sim_time, accident_info, log, voice_queue):
    """Updates the logic for ALL cars based on the scripted time."""
    
    # --- 1. SCRIPTED CAR STARTS ---
    if sim_time == 1:
        cars['1']['status'] = 'Normal'
        cars['1']['speed'] = NORMAL_SPEED
        add_log_entry(log, "Car 1 is on the road.", voice_queue, speak=True)
    if sim_time == CAR_2_START_TIME:
        cars['2']['status'] = 'Normal'
        cars['2']['speed'] = NORMAL_SPEED
        add_log_entry(log, "Car 2 is on the road.", voice_queue, speak=True)
    if sim_time == CAR_3_START_TIME:
        cars['3']['status'] = 'Normal'
        cars['3']['speed'] = NORMAL_SPEED
        add_log_entry(log, "Car 3 is on the road.")
    if sim_time == CAR_4_START_TIME:
        cars['4']['status'] = 'Normal'
        cars['4']['speed'] = NORMAL_SPEED
        add_log_entry(log, "Car 4 is on the road.")

    # --- 2. SCRIPTED CRASH ---
    if not accident_info and sim_time >= CRASH_TIME and cars['2']['x'] >= BLACKSPOT_B:
        cars['2']['status'] = 'Crashed'
        cars['2']['speed'] = 0
        cars['2']['x'] = BLACKSPOT_B # Pin to exact spot
        accident_info = {'id': '2', 'x': BLACKSPOT_B}
        add_log_entry(log, "CRITICAL: Car 2 has crashed at Blackspot B! Broadcasting ATOA alert!", voice_queue, speak=True)
    
    # --- 3. UPDATE EACH CAR'S LOGIC ---
    for car_id in ['1', '2', '3', '4']:
        car = cars[car_id]
        if car['status'] == 'Waiting' or car['status'] == 'Finished' or car['status'] == 'Crashed':
            continue # Don't move
            
        old_status = car['status']

        # --- ATOA LOGIC ---
        if accident_info and car['status'] == 'Normal' and car['id'] not in ['1', '2']:
            car['status'] = 'Braking (Alert)'
            car['alert_message'] = "🚨 ATOA Alert!"
            add_log_entry(log, f"Car {car_id}: Received broadcast! Accident ahead. Braking.", voice_queue, speak=True)

        # --- FIND CAR IN FRONT ---
        car_in_front = None
        if car_id == '2': car_in_front = cars['1']
        if car_id == '3': car_in_front = cars['2']
        if car_id == '4': car_in_front = cars['3']

        distance = 999
        if car_in_front and car_in_front['x'] > car['x']:
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
            if car_id == '1':
                add_log_entry(log, "Car 1 finished safely.")

    return accident_info


def render_full_road(cars):
    """
    Renders the full road with all cars, like the obj2 simulation.
    """
    road = ["-"] * (ROAD_LENGTH + 1) # Create the road
    road[0] = "A" # Start Point
    road[ROAD_LENGTH] = "G" # End Point
    
    # Place a marker for the blackspot
    road[BLACKSPOT_B] = "B" 
    
    # Place a fog marker to show what drivers can see
    fog_marker_pos = int(BLACKSPOT_B - VISIBILITY_DISTANCE)
    if 0 < fog_marker_pos < ROAD_LENGTH and road[fog_marker_pos] == "-":
        road[fog_marker_pos] = "|" # "|" = Fog visibility limit
    
    # Place cars on the road
    for car_id in ['4', '3', '2', '1']: # Draw in reverse order
        car = cars[car_id]
        pos = int(math.floor(car['x']))

        if 0 <= pos <= ROAD_LENGTH:
            symbol = car_id # Default
            if car['status'] == 'Crashed': symbol = "💥"
            elif car['status'] == 'Stopped': symbol = "🛑"
            elif car['status'] == 'Braking (Alert)': symbol = car_id.lower() # "3", "4"
            
            # Don't overwrite Start, End, or Blackspot
            if road[pos] in ["-", "|"]:
                road[pos] = symbol
            elif car['status'] == 'Crashed': # Crash overrides Blackspot
                road[pos] = "💥"
            
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
    st.markdown(f"**Road `A` (Start) to `G` (End)** | **Blackspot at `B`** | **Fog Visibility:** `{VISIBILITY_DISTANCE:.1f} units` (Indicated by `|`)")
    
    # --- SINGLE ROAD DISPLAY ---
    st.subheader("Full Road View")
    road_placeholder = st.empty()
    
    # --- CAR STATUS ---
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        car1_status = st.empty()
    with col2:
        car2_status = st.empty()
    with col3:
        car3_status = st.empty()
    with col4:
        car4_status = st.empty()
        
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
    road_placeholder.code(render_full_road(st.session_state.cars), language="text")

    # --- 4. Render Status Metrics ---
    car1_status.metric("Car 1", st.session_state.cars['1']['status'], f"{int(st.session_state.cars['1']['x'])}m")
    car2_status.metric("Car 2", st.session_state.cars['2']['status'], f"{int(st.session_state.cars['2']['x'])}m")
    
    # Highlight the "saved" cars
    if st.session_state.cars['3']['status'] == 'Braking (Alert)':
        car3_status.metric("Car 3", st.session_state.cars['3']['status'], "ATOA ALERT!")
    else:
        car3_status.metric("Car 3", st.session_state.cars['3']['status'], f"{int(st.session_state.cars['3']['x'])}m")
    
    if st.session_state.cars['4']['status'] == 'Braking (Alert)':
        car4_status.metric("Car 4", st.session_state.cars['4']['status'], "ATOA ALERT!")
    else:
        car4_status.metric("Car 4", st.session_state.cars['4']['status'], f"{int(st.session_state.cars['4']['x'])}m")


    # --- 5. Process Voice Alerts (Hidden) ---
    voice_html = speak_alerts(st.session_state.voice_queue)
    voice_placeholder.empty() 
    voice_placeholder.write(components.html(voice_html, height=0))

    # --- 6. Increment time and rerun ---
    st.session_state.sim_time += 1

    # Check for end condition
    if all(c['status'] in ['Finished', 'Stopped', 'Crashed'] for c in st.session_state.cars.values()):
        st.session_state.simulation_running = False
        st.success("Simulation Demo Finished.")
        if st.session_state.cars['3']['status'] == 'Stopped' and st.session_state.cars['4']['status'] == 'Stopped':
             st.success("Proof of Concept: Cars 3 and 4 received the ATOA alert and stopped safely!")
        st.balloons()
    else:
        time.sleep(0.3) # Control the simulation speed
        st.rerun()

else:
    st.info("Press 'Start Simulation' in the sidebar to begin.")
