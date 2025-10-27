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
ROAD_LENGTH = 200  # Total length of the "looping" road
NORMAL_SPEED = 2
BRAKING_SPEED = 1
# Fog reduces visibility. 80 fog = 10 visibility.
VISIBILITY_DISTANCE = 50 * (1 - fog_level / 100.0)
# Minimum distance needed to stop
BRAKING_DISTANCE = 15 
# Probability of a random car crashing per tick
ACCIDENT_PROBABILITY = 0.01
# How long an accident stays on the road (in seconds)
ACCIDENT_DURATION_S = 20 

# -----------------------
# HELPER FUNCTIONS
# -----------------------

def get_time():
    """Helper to get a simple timestamp for the log."""
    return datetime.now().strftime("%H:%M:%S")

def add_log_entry(log, message, voice_queue=None, speak=False):
    """Adds a new entry to the top of a log list and queues voice."""
    entry = f"[{get_time()}] {message}"
    if entry not in log: # Avoid duplicate log entries
        log.insert(0, entry)
        if speak and voice_queue is not None:
            voice_queue.append(message)

def initialize_cars(road_id, num_cars):
    """Creates a list of car dictionaries for a road."""
    cars = []
    for i in range(num_cars):
        cars.append({
            'id': f"{road_id}-{i+1}", # Start from 1 for clarity
            'x': (i * (ROAD_LENGTH / num_cars)) % ROAD_LENGTH,  
            'speed': NORMAL_SPEED,
            'status': 'Normal', # Normal, Braking (Alert), Braking (Visual), Stopped, Crashed
            'alert_message': 'All clear.',
        })
    return cars

def update_road_logic(cars, accident_info, log, voice_queue):
    """
    Updates the logic for one road.
    Handles car movement, wrapping, visual checks, and ATOA alerts.
    """
    cars.sort(key=lambda c: c['x'], reverse=True) # Lead car is always index 0

    for i in range(len(cars)):
        car = cars[i]
        
        # --- Find the car in front (handles loop-around) ---
        car_in_front = cars[i-1] if i > 0 else cars[-1]
        
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
        
        # A. Check for visual on the car in front
        if distance <= VISIBILITY_DISTANCE:
            # If the car in front is crashed...
            if car_in_front['status'] == 'Crashed':
                # ...is it too late to stop?
                if distance <= BRAKING_DISTANCE:
                    car['status'] = 'Crashed' 
                    car['alert_message'] = "CRASHED!"
                else:
                    # ...no, driver can see it and brake.
                    if car['status'] == 'Normal':
                        car['status'] = 'Braking (Visual)'
                        car['alert_message'] = "Driver: Crash Spotted!"
            
            # If car in front is just braking or stopped, driver should also brake/stop.
            elif car_in_front['status'].startswith('Braking') and car['status'] == 'Normal':
                car['status'] = 'Braking (Visual)'
                car['alert_message'] = "Driver: Brakes Spotted!"
            elif car_in_front['status'] == 'Stopped' and car['status'] == 'Normal':
                car['status'] = 'Braking (Visual)'
                car['alert_message'] = "Driver: Stopped Car!"

        # B. If car is braking (from alert or visual), manage its speed
        if car['status'].startswith('Braking'):
            car['speed'] = BRAKING_SPEED
            # Logic to stop safely before the obstacle
            if distance <= (BRAKING_DISTANCE + 5): # Stop 5 units behind
                car['status'] = 'Stopped'
                car['alert_message'] = "Stopped Safely."
        
        # C. If no alerts and no visual, drive normally
        elif car['status'] == 'Normal':
            car['speed'] = NORMAL_SPEED
            car['alert_message'] = 'All clear.'
            # Simple follow logic to avoid bumping
            if distance < (BRAKING_DISTANCE + 10): # Keep a 10-unit buffer
                car['speed'] = BRAKING_SPEED
        
        # --- 3. Log state changes for voice ---
        if car['status'] != old_status and not car['status'] == 'Crashed':
            log_msg = f"Car {car['id']}: {car['alert_message']}"
            if car['status'] == 'Braking (Visual)':
                add_log_entry(log, log_msg, voice_queue, speak=True)
            elif car['status'] == 'Stopped':
                add_log_entry(log, log_msg)
        elif car['status'] == 'Crashed' and old_status != 'Crashed':
             add_log_entry(log, f"Car {car['id']}: CRASHED! (Chain reaction).", voice_queue, speak=True)


        # --- 4. Move the car and loop it ---
        if car['status'] != 'Stopped':
            car['x'] += car['speed']
            car['x'] = car['x'] % ROAD_LENGTH # Wrap around the road

def render_drivers_view(driver_car, all_cars):
    """
    *** THIS IS THE KEY PROOF-OF-CONCEPT FUNCTION ***
    Renders the road from the driver's perspective, including fog.
    """
    view_length = 50 # How far the driver's "dashboard" view shows
    road = ["-"] * view_length
    
    # Place the driver's car
    road[0] = "🚘"
    
    for car in all_cars:
        if car['id'] == driver_car['id']:
            continue
            
        # Calculate distance to this car
        if car['x'] > driver_car['x']:
            distance = car['x'] - driver_car['x']
        else:
            distance = (ROAD_LENGTH - driver_car['x']) + car['x']
            
        if 0 < distance < view_length:
            symbol = "?" # Default
            
            # Is the car visible through the fog?
            if distance <= VISIBILITY_DISTANCE:
                if car['status'] == 'Crashed':
                    symbol = "💥"
                elif car['status'] == 'Stopped':
                    symbol = "🛑"
                elif car['status'].startswith('Braking'):
                    symbol = "B" 
                else:
                    symbol = "🚘"
            else:
                symbol = "▒" # Fog
                
            road[int(distance)] = symbol
            
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
    st.session_state.road_1_alert_log = [f"[{get_time()}] Road 1 monitoring... All clear."]
    st.session_state.road_2_alert_log = [f"[{get_time()}] Road 2 monitoring... All clear."]

if stop_button:
    st.session_state.simulation_running = False
    st.rerun() # Force a stop and clear the loop

# -----------------------
# MAIN SIMULATION RENDER
# -----------------------
if st.session_state.simulation_running:
    
    # --- Placeholders for all UI elements ---
    st.markdown(f"**Fog Visibility:** `{VISIBILITY_DISTANCE:.1f} units` | **Safe Braking Distance:** `{BRAKING_DISTANCE} units`")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Road 1 (Control - No Alerts)")
        dash1_placeholder = st.empty()
        log1_box = st.expander("Road 1: Voice Assistant Log")
    
    with col2:
        st.subheader("Road 2 (ATOA Protected)")
        dash2_placeholder = st.empty()
        log2_box = st.expander("Road 2: Voice Assistant Log", expanded=True)
        
    voice_placeholder = st.empty()
    
    # --- 1. Clear voice queue ---
    st.session_state.voice_queue = []

    # --- 2. Check for new RANDOM accident on Road 2 ---
    if not st.session_state.road_2_accident: 
        if random.random() < ACCIDENT_PROBABILITY:
            # Pick a random car to crash
            car_to_crash = random.choice(st.session_state.road_2_cars)
            if car_to_crash['status'] == 'Normal': # Only crash normal cars
                car_to_crash['status'] = 'Crashed'
                st.session_state.road_2_accident = {'id': car_to_crash['id'], 'x': car_to_crash['x'], 'time': time.time()}
                
                st.warning(f"💥 Accident Occurred on Road 2 at position {int(car_to_crash['x'])}!")
                add_log_entry(st.session_state.road_2_alert_log, 
                              f"CRITICAL: Accident detected! Broadcasting ATOA alert!",
                              st.session_state.voice_queue, speak=True)
    
    # --- 3. Check if accident should be CLEARED ---
    if st.session_state.road_2_accident:
        if time.time() - st.session_state.road_2_accident['time'] > ACCIDENT_DURATION_S:
            add_log_entry(st.session_state.road_2_alert_log, "INFO: Accident has been cleared. Resuming normal traffic.", st.session_state.voice_queue, speak=True)
            # Find the crashed car and reset it
            for car in st.session_state.road_2_cars:
                if car['id'] == st.session_state.road_2_accident['id']:
                    car['status'] = 'Normal'
            st.session_state.road_2_accident = None

    # --- 4. Update logic for both roads ---
    update_road_logic(st.session_state.road_1_cars, None, st.session_state.road_1_alert_log, st.session_state.voice_queue) 
    update_road_logic(st.session_state.road_2_cars, st.session_state.road_2_accident, st.session_state.road_2_alert_log, st.session_state.voice_queue)

    # --- 5. Render the simulation ---
    
    # --- Render Road 1 Dashboard ---
    driver1 = st.session_state.road_1_cars[0] # Focus on Car A-1
    road1_view = render_drivers_view(driver1, st.session_state.road_1_cars)
    dash1_placeholder.code(f"Driver's View: {road1_view}", language="text")
    log1_box.write(st.session_state.road_1_alert_log)
    
    # --- Render Road 2 Dashboard (The Proof!) ---
    driver2 = st.session_state.road_2_cars[0] # Focus on Car B-1
    road2_view = render_drivers_view(driver2, st.session_state.road_2_cars)
    dash2_placeholder.code(f"Driver's View: {road2_view}", language="text")
    log2_box.write(st.session_state.road_2_alert_log)

    # --- Display Status Metrics for all cars ---
    with col1:
        for car in st.session_state.road_1_cars:
            st.metric(f"Car {car['id']} (Pos: {int(car['x'])})", car['status'])
    with col2:
        for car in st.session_state.road_2_cars:
            if car['status'] == 'Crashed':
                st.metric(f"Car {car['id']} (Pos: {int(car['x'])})", car['status'], "CRASHED")
            elif car['status'] == 'Braking (Alert)':
                st.metric(f"Car {car['id']} (Pos: {int(car['x'])})", car['status'], "ATOA ALERT")
            else:
                st.metric(f"Car {car['id']} (Pos: {int(car['x'])})", car['status'])

    # --- 6. Process Voice Alerts ---
    voice_html = speak_alerts(st.session_state.voice_queue)
    voice_placeholder.empty() # Clear old JS
    voice_placeholder.write(components.html(voice_html, height=0))

    # --- 7. Rerun loop ---
    time.sleep(0.4) # Slightly slower for better visibility
    st.rerun()

else:
    st.info("Press 'Start Simulation' in the sidebar to begin.")
