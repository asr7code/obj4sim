import streamlit as st
import streamlit.components.v1 as components
import random
import time
from datetime import datetime

# -----------------------
# PAGE CONFIGURATION
# -----------------------
st.set_page_config(page_title="ATOA Simulation", layout="wide")
st.title("🚨 AI-Based Advanced Traffic Optimizer & Assistant (ATOA)")
st.subheader("Accident Prevention System: Proof of Concept")

# -----------------------
# SIDEBAR CONTROLS
# -----------------------
st.sidebar.header("Simulation Controls")
num_cars = st.sidebar.slider("Number of Cars per Road", 2, 5, 3, help="How many cars on each road.")
fog_level = st.sidebar.slider("Fog Level (Reduces Visibility)", 0, 90, 80, help="High fog = low visibility. Drivers can't see far.")
run_button = st.sidebar.button("▶ Start Simulation")
stop_button = st.sidebar.button("■ Stop Simulation")

# -----------------------
# SIMULATION CONSTANTS
# -----------------------
ROAD_LENGTH = 200
NORMAL_SPEED = 2
BRAKING_SPEED = 1
VISIBILITY_DISTANCE = 50 * (1 - fog_level / 100.0)
BRAKING_DISTANCE = 15 
ACCIDENT_PROBABILITY = 0.01
ACCIDENT_DURATION_S = 20 

# -----------------------
# HELPER FUNCTIONS
# -----------------------

def get_time():
    """Helper to get a simple timestamp for the log."""
    return datetime.now().strftime("%H:%M:%S")

def add_log_entry(log, message, voice_queue=None, speak=False):
    """Adds to log (for voice logic) but log is not displayed."""
    entry = f"[{get_time()}] {message}"
    # Avoid duplicate log entries
    if not log or log[0] != entry:
        log.insert(0, entry)
        if speak and voice_queue is not None:
            voice_queue.append(message)

def initialize_cars(road_id, num_cars):
    """Creates a list of car dictionaries for a road."""
    cars = []
    for i in range(num_cars):
        cars.append({
            'id': f"{road_id}-{i+1}",
            'x': (i * (ROAD_LENGTH / num_cars)) % ROAD_LENGTH,  
            'speed': NORMAL_SPEED,
            'status': 'Normal',
            'alert_message': 'All clear.',
        })
    return cars

def update_road_logic(cars, accident_info, log, voice_queue):
    """Updates the logic for one road."""
    cars.sort(key=lambda c: c['x'], reverse=True) # Lead car is always index 0

    for i in range(len(cars)):
        car = cars[i]
        car_in_front = cars[i-1] if i > 0 else cars[-1] # Find car in front (handles loop)
        
        # Calculate distance, handling the road loop
        if car_in_front['x'] > car['x']:
            distance = car_in_front['x'] - car['x']
        else:
            distance = (ROAD_LENGTH - car['x']) + car_in_front['x']

        # --- Reset status if obstacle is gone ---
        if car['status'] == 'Stopped' and (car_in_front['status'] != 'Stopped' and car_in_front['status'] != 'Crashed'):
            car['status'] = 'Normal'
        if car['status'].startswith('Braking') and (not accident_info or car['x'] > accident_info['x']):
            car['status'] = 'Normal' # Clear alert if we passed the accident

        # --- Skip cars that are crashed ---
        if car['status'] == 'Crashed':
            car['speed'] = 0
            continue
            
        old_status = car['status'] # Store status to check for changes

        # --- 1. ATOA ALERT LOGIC (Your Project's Feature) ---
        if accident_info and car['x'] < accident_info['x'] and car['status'] == 'Normal':
            car['status'] = 'Braking (Alert)'
            car['alert_message'] = f"🚨 ATOA Alert: Accident Ahead!"
            add_log_entry(log, f"Car {car['id']}: Received broadcast! Accident at {int(accident_info['x'])}. Braking.", voice_queue, speak=True)
        
        # --- 2. DRIVER VISUAL LOGIC (Normal Human Driving) ---
        if distance <= VISIBILITY_DISTANCE:
            if car_in_front['status'] == 'Crashed':
                if distance <= BRAKING_DISTANCE:
                    car['status'] = 'Crashed' 
                    car['alert_message'] = "CRASHED!"
                else:
                    if car['status'] == 'Normal':
                        car['status'] = 'Braking (Visual)'
                        car['alert_message'] = "Driver: Crash Spotted!"
            
            elif car_in_front['status'].startswith('Braking') and car['status'] == 'Normal':
                car['status'] = 'Braking (Visual)'
                car['alert_message'] = "Driver: Brakes Spotted!"
            elif car_in_front['status'] == 'Stopped' and car['status'] == 'Normal':
                car['status'] = 'Braking (Visual)'
                car['alert_message'] = "Driver: Stopped Car!"

        # --- 3. Manage Speed ---
        if car['status'].startswith('Braking'):
            car['speed'] = BRAKING_SPEED
            if distance <= (BRAKING_DISTANCE + 5): # Stop 5 units behind
                car['status'] = 'Stopped'
                car['alert_message'] = "Stopped Safely."
        
        elif car['status'] == 'Normal':
            car['speed'] = NORMAL_SPEED
            car['alert_message'] = 'All clear.'
            # Simple follow logic to avoid bumping
            if distance < (BRAKING_DISTANCE + 10): 
                car['speed'] = BRAKING_SPEED
        
        # --- 4. Log state changes for voice ---
        if car['status'] != old_status and not car['status'] == 'Crashed':
            log_msg = f"Car {car['id']}: {car['alert_message']}"
            if car['status'] == 'Braking (Visual)':
                add_log_entry(log, log_msg, voice_queue, speak=True)
            elif car['status'] == 'Stopped':
                add_log_entry(log, log_msg)
        elif car['status'] == 'Crashed' and old_status != 'Crashed':
             add_log_entry(log, f"Car {car['id']}: CRASHED! (Chain reaction).", voice_queue, speak=True)

        # --- 5. Move the car ---
        if car['status'] != 'Stopped':
            car['x'] += car['speed']
            car['x'] = car['x'] % ROAD_LENGTH # Wrap around the road

def render_drivers_view(driver_car, all_cars):
    """Renders the road from the driver's perspective, including fog."""
    view_length = 50 
    road = ["-"] * view_length
    road[0] = "🚘"
    
    # Create a dictionary for occupied positions to prevent overwrites
    occupied_positions = {}

    for car in all_cars:
        if car['id'] == driver_car['id']:
            continue
            
        # Calculate distance to this car
        if car['x'] > driver_car['x']:
            distance = car['x'] - driver_car['x']
        else:
            distance = (ROAD_LENGTH - driver_car['x']) + car['x']
            
        if 0 < distance < view_length:
            distance_int = int(distance)
            symbol = "?"
            
            if distance <= VISIBILITY_DISTANCE:
                # Car is visible
                if car['status'] == 'Crashed':
                    symbol = "💥"
                elif car['status'] == 'Stopped':
                    symbol = "🛑"
                elif car['status'] == 'Braking (Alert)':
                    symbol = "B" # 'B' for ATOA Braking
                else:
                    symbol = "🚘"
            else:
                # Car is in the fog
                symbol = "▒" 
            
            # Add to dictionary, prioritizing closer cars
            if distance_int not in occupied_positions or occupied_positions[distance_int] == "▒":
                occupied_positions[distance_int] = symbol

    # Fill the road string from the dictionary
    for pos, symbol in occupied_positions.items():
        road[pos] = symbol
            
    return "".join(road)

def speak_alerts(voice_queue):
    """Generates JS to speak all queued alerts."""
    if not voice_queue:
        return ""
    
    script = "<script>"
    for alert_text in voice_queue:
        # Clean text for JS
        alert_text = alert_text.replace("'", "").replace('"', "")
        script += f"""
            var msg = new SpeechSynthesisUtterance('{alert_text}');
            window.speechSynthesis.speak(msg);
        """
    script += "</script>"
    return script

# -----------------------
# INITIALIZE SESSION STATE
# -----------------------
if 'simulation_running' not in st.session_state:
    st.session_state.simulation_running = False

if run_button:
    st.session_state.road_1_cars = initialize_cars("A", num_cars)
    st.session_state.road_2_cars = initialize_cars("B", num_cars)
    st.session_state.road_2_accident = None 
    st.session_state.simulation_running = True
    # Logs are still needed in the backend for voice logic
    st.session_state.road_1_alert_log = [f"[{get_time()}] Road 1 monitoring... All clear."]
    st.session_state.road_2_alert_log = [f"[{get_time()}] Road 2 monitoring... All clear."]

if stop_button:
    st.session_state.simulation_running = False
    st.rerun() 

# -----------------------
# MAIN SIMULATION RENDER
# -----------------------
if st.session_state.simulation_running:
    
    # --- Placeholders for UI elements ---
    st.markdown(f"**Fog Visibility:** `{VISIBILITY_DISTANCE:.1f} units` | **Safe Braking Distance:** `{BRAKING_DISTANCE} units`")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Road 1 (Control - No Alerts)")
        dash1_placeholder = st.empty()
    
    with col2:
        st.subheader("Road 2 (ATOA Protected)")
        dash2_placeholder = st.empty()
        
    # This placeholder is the fix. It will be hidden.
    voice_placeholder = st.empty()
    
    # --- 1. Clear voice queue ---
    st.session_state.voice_queue = []

    # --- 2. Check for new RANDOM accident on Road 2 ---
    if not st.session_state.road_2_accident: 
        if random.random() < ACCIDENT_PROBABILITY:
            car_to_crash = random.choice(st.session_state.road_2_cars)
            if car_to_crash['status'] == 'Normal':
                car_to_crash['status'] = 'Crashed'
                st.session_state.road_2_accident = {'id': car_to_crash['id'], 'x': car_to_crash['x'], 'time': time.time()}
                add_log_entry(st.session_state.road_2_alert_log, 
                              f"CRITICAL: Accident detected! Broadcasting ATOA alert!",
                              st.session_state.voice_queue, speak=True)
    
    # --- 3. Check if accident should be CLEARED ---
    if st.session_state.road_2_accident:
        if time.time() - st.session_state.road_2_accident['time'] > ACCIDENT_DURATION_S:
            add_log_entry(st.session_state.road_2_alert_log, "INFO: Accident has been cleared. Resuming normal traffic.", st.session_state.voice_queue, speak=True)
            for car in st.session_state.road_2_cars:
                if car['id'] == st.session_state.road_2_accident['id']:
                    car['status'] = 'Normal'
            st.session_state.road_2_accident = None

    # --- 4. Update logic for both roads ---
    update_road_logic(st.session_state.road_1_cars, None, st.session_state.road_1_alert_log, st.session_state.voice_queue) 
    update_road_logic(st.session_state.road_2_cars, st.session_state.road_2_accident, st.session_state.road_2_alert_log, st.session_state.voice_queue)

    # --- 5. Render the simulation (Driver's View ONLY) ---
    
    # --- Render Road 1 Dashboard ---
    driver1 = st.session_state.road_1_cars[0] # Focus on Car A-1
    road1_view = render_drivers_view(driver1, st.session_state.road_1_cars)
    dash1_placeholder.code(f"Driver's View (Car A-1): {road1_view}", language="text")
    
    # --- Render Road 2 Dashboard (The Proof!) ---
    driver2 = st.session_state.road_2_cars[0] # Focus on Car B-1
    road2_view = render_drivers_view(driver2, st.session_state.road_2_cars)
    dash2_placeholder.code(f"Driver's View (Car B-1): {road2_view}", language="text")

    # --- 6. Process Voice Alerts (Hidden) ---
    # This is the corrected part. 
    # It writes the invisible HTML component into the placeholder.
    voice_html = speak_alerts(st.session_state.voice_queue)
    voice_placeholder.empty() 
    voice_placeholder.write(components.html(voice_html, height=0))

    # --- 7. Rerun loop ---
    time.sleep(0.4)
    st.rerun()

else:
    st.info("Press 'Start Simulation' in the sidebar to begin.")
