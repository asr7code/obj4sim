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
# Probability of an accident per tick for the lead car
ACCIDENT_PROBABILITY = 0.02
# How long an accident stays on the road (in seconds)
ACCIDENT_DURATION_S = 30 

# -----------------------
# HELPER FUNCTIONS
# -----------------------

def get_time():
    """Helper to get a simple timestamp for the log."""
    return datetime.now().strftime("%H:%M:%S")

def add_log_entry(log, message, voice_queue=None, speak=False):
    """Adds a new entry to the top of a log list and queues voice."""
    log.insert(0, f"[{get_time()}] {message}")
    if speak and voice_queue is not None:
        voice_queue.append(message)

def initialize_cars(road_id, num_cars):
    """Creates a list of car dictionaries for a road."""
    cars = []
    for i in range(num_cars):
        cars.append({
            'id': f"{road_id}-{i}",
            # Space cars out evenly on the looping road
            'x': (i * (ROAD_LENGTH / num_cars)) % ROAD_LENGTH,  
            'speed': NORMAL_SPEED,
            'status': 'Normal', # Normal, Braking (Alert), Braking (Visual), Stopped, Crashed
            'alert_message': 'All clear.',
            'log_alerted': False # Flag to prevent log spam
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
        
        # --- Reset log_alerted flag if car is normal ---
        if car['status'] == 'Normal':
            car['log_alerted'] = False
            car['alert_message'] = 'All clear.'

        # --- Skip cars that are stopped or crashed ---
        if car['status'] in ['Stopped', 'Crashed']:
            car['speed'] = 0
            continue

        # --- 1. ATOA ALERT LOGIC (Your Project's Feature) ---
        if accident_info and car['x'] < accident_info['x'] and not car['log_alerted']:
            car['alert_message'] = f"🚨 ATOA Alert!"
            car['status'] = 'Braking (Alert)'
            add_log_entry(log, f"Car {car['id']}: Received broadcast! Accident at {int(accident_info['x'])}. Braking.", voice_queue, speak=True)
            car['log_alerted'] = True # Mark as alerted

        # --- 2. DRIVER VISUAL LOGIC (Normal Human Driving) ---
        # Find the car in front (handles loop-around)
        car_in_front = cars[i-1] if i > 0 else cars[-1]
        
        # Calculate distance, handling the road loop
        if car_in_front['x'] > car['x']:
            distance = car_in_front['x'] - car['x']
        else:
            distance = (ROAD_LENGTH - car['x']) + car_in_front['x']

        # A. Check for visual on the car in front
        if distance <= VISIBILITY_DISTANCE:
            # If the car in front is crashed...
            if car_in_front['status'] == 'Crashed':
                # ...is it too late to stop?
                if distance <= BRAKING_DISTANCE:
                    car['status'] = 'Crashed' # 💥 Chain reaction!
                    car['alert_message'] = "CRASHED!"
                    if not car['log_alerted']:
                        add_log_entry(log, f"Car {car['id']}: CRASHED! (Too late to see).", voice_queue, speak=True)
                        car['log_alerted'] = True
                else:
                    # ...no, driver can see it and brake.
                    if not car['status'].startswith('Braking'):
                        car['status'] = 'Braking (Visual)'
                        car['alert_message'] = "Driver: Crash!"
                        if not car['log_alerted']:
                            add_log_entry(log, f"Car {car['id']}: Driver spotted crash. Braking.")
                            car['log_alerted'] = True
            
            # If car in front is just braking, driver should also brake.
            elif car_in_front['status'].startswith('Braking') and car['status'] == 'Normal':
                car['status'] = 'Braking (Visual)'
                car['alert_message'] = "Driver: Brakes!"
        
        # B. If car is braking (from alert or visual), manage its speed
        if car['status'].startswith('Braking'):
            car['speed'] = BRAKING_SPEED
            # Logic to stop safely before the obstacle
            obstacle_x = accident_info['x'] if accident_info else car_in_front['x']
            
            if car['x'] >= (obstacle_x - BRAKING_DISTANCE - 5) % ROAD_LENGTH: 
                if car['status'] != 'Stopped':
                    car['status'] = 'Stopped'
                    car['alert_message'] = "Stopped."
                    add_log_entry(log, f"Car {car['id']}: Stopped safely.")
        
        # C. If no alerts and no visual, drive normally
        elif car['status'] == 'Normal':
            car['speed'] = NORMAL_SPEED
            # Simple follow logic to avoid bumping
            if distance < (BRAKING_DISTANCE + 10): # Keep a 10-unit buffer
                car['speed'] = BRAKING_SPEED


        # --- 3. Move the car and loop it ---
        car['x'] += car['speed']
        car['x'] = car['x'] % ROAD_LENGTH # Wrap around the road

def render_road(cars):
    """Creates a text-based string for the road."""
    display_length = 100 # Keep display 100 chars
    road = ["-"] * display_length
    for car in reversed(cars): # Draw back-to-front
        pos = int(car['x'] / ROAD_LENGTH * display_length)
        pos = min(pos, display_length - 1)
        
        if 0 <= pos < display_length:
            if car['status'] == 'Crashed':
                road[pos] = "💥"
            elif car['status'] == 'Stopped':
                road[pos] = "🛑" 
            elif car['status'].startswith('Braking'):
                road[pos] = "B" 
            else:
                road[pos] = "🚘" 
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
    st.session_state.voice_queue = []

if stop_button:
    st.session_state.simulation_running = False

# -----------------------
# MAIN SIMULATION RENDER
# -----------------------
if st.session_state.simulation_running:
    
    # --- Placeholders for all UI elements ---
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Road 1 (Control - No Alerts)")
        road1_box = st.code("", language="text")
        log1_box = st.expander("Road 1: Voice Assistant Log")
        info1_cols = st.columns(num_cars)
    
    with col2:
        st.subheader("Road 2 (ATOA Protected)")
        road2_box = st.code("", language="text")
        log2_box = st.expander("Road 2: Voice Assistant Log", expanded=True)
        info2_cols = st.columns(num_cars)
        
    st.markdown("---")
    st.markdown(f"**Fog Visibility:** {VISIBILITY_DISTANCE:.1f} units | **Safe Braking Distance:** {BRAKING_DISTANCE} units")
    voice_placeholder = st.empty()
    
    # --- 1. Clear voice queue ---
    st.session_state.voice_queue = []

    # --- 2. Check for new RANDOM accident on Road 2 ---
    if not st.session_state.road_2_accident: 
        lead_car_2 = sorted(st.session_state.road_2_cars, key=lambda c: c['x'], reverse=True)[0]
        if random.random() < ACCIDENT_PROBABILITY:
            lead_car_2['status'] = 'Crashed'
            st.session_state.road_2_accident = {'x': lead_car_2['x'], 'time': time.time()}
            
            st.warning(f"💥 Accident Occurred on Road 2 at position {int(lead_car_2['x'])}!")
            add_log_entry(st.session_state.road_2_alert_log, 
                          f"CRITICAL: Accident detected at {int(lead_car_2['x'])}. Broadcasting ATOA alert!",
                          st.session_state.voice_queue, speak=True)
    
    # --- 3. Check if accident should be CLEARED ---
    if st.session_state.road_2_accident:
        if time.time() - st.session_state.road_2_accident['time'] > ACCIDENT_DURATION_S:
            add_log_entry(st.session_state.road_2_alert_log, "INFO: Accident has been cleared. Resuming normal traffic.", st.session_state.voice_queue, speak=True)
            # Find the crashed car and reset it
            for car in st.session_state.road_2_cars:
                if car['status'] == 'Crashed':
                    car['status'] = 'Normal'
            st.session_state.road_2_accident = None

    # --- 4. Update logic for both roads ---
    update_road_logic(st.session_state.road_1_cars, None, st.session_state.road_1_alert_log, st.session_state.voice_queue) 
    update_road_logic(st.session_state.road_2_cars, st.session_state.road_2_accident, st.session_state.road_2_alert_log, st.session_state.voice_queue)

    # --- 5. Render the simulation ---
    road1_box.code(render_road(st.session_state.road_1_cars))
    log1_box.write(st.session_state.road_1_alert_log)
    
    road2_box.code(render_road(st.session_state.road_2_cars))
    log2_box.write(st.session_state.road_2_alert_log)

    for i in range(num_cars):
        car1 = st.session_state.road_1_cars[i]
        with info1_cols[i]:
            st.metric(f"Car {car1['id']} (Pos: {int(car1['x'])})", car1['status'])

        car2 = st.session_state.road_2_cars[i]
        with info2_cols[i]:
            st.metric(f"Car {car2['id']} (Pos: {int(car2['x'])})", car2['status'])
            if car2['status'] == 'Crashed':
                st.error(car2['alert_message'])
            elif car2['status'] == 'Braking (Alert)':
                st.warning(car2['alert_message'])
            elif car2['status'] != 'Normal':
                st.info(car2['alert_message'])
    
    # --- 6. Process Voice Alerts ---
    voice_html = speak_alerts(st.session_state.voice_queue)
    voice_placeholder.empty()
    voice_placeholder.write(components.html(voice_html, height=0))

    # --- 7. Rerun loop ---
    time.sleep(0.3)
    st.rerun()

else:
    st.info("Press 'Start Simulation' in the sidebar to begin.")
