import streamlit as st
import random
import time

# -----------------------
# PAGE CONFIGURATION
# -----------------------
st.set_page_config(page_title="Accident Prevention Sim", layout="wide")
st.title("🚨 Accident Prevention Simulation (ATOA)")
st.markdown("This simulation demonstrates how the ATOA system prevents chain-reaction accidents in low-visibility (fog) conditions.")

# -----------------------
# SIDEBAR CONTROLS
# -----------------------
st.sidebar.header("Simulation Controls")
num_cars = st.sidebar.slider("Number of Cars per Road", 2, 5, 3)
fog_level = st.sidebar.slider("Fog Level (Reduces Visibility)", 0, 90, 70)
run_button = st.sidebar.button("▶ Start Simulation")

# -----------------------
# SIMULATION CONSTANTS
# -----------------------
ROAD_LENGTH = 100
NORMAL_SPEED = 2
BRAKING_SPEED = 1
# Fog reduces visibility. 0 fog = 50 visibility. 100 fog = 0 visibility.
VISIBILITY_DISTANCE = 50 * (1 - fog_level / 100.0)
# Minimum distance needed to stop
BRAKING_DISTANCE = 15 
# Probability of an accident per tick for the lead car
ACCIDENT_PROBABILITY = 0.05 

# -----------------------
# HELPER FUNCTIONS
# -----------------------

def initialize_cars(road_id):
    """Creates a list of car dictionaries for a road."""
    cars = []
    for i in range(num_cars):
        cars.append({
            'id': f"{road_id}-{i}",
            'x': (num_cars - i - 1) * 20,  # Start spaced out
            'speed': NORMAL_SPEED,
            'status': 'Normal', # Normal, Braking (Alert), Braking (Visual), Stopped, Crashed
            'alert': None
        })
    return cars

def update_road_logic(cars, accident_info):
    """
    Updates the logic for one road.
    Handles car movement, visual checks, and ATOA alerts.
    """
    for i in range(len(cars)):
        car = cars[i]
        
        # --- Skip cars that are stopped or crashed ---
        if car['status'] in ['Stopped', 'Crashed']:
            car['speed'] = 0
            continue

        # --- 1. ATOA ALERT LOGIC (Your Project's Feature) ---
        # Does this car have an active alert?
        if accident_info and car['status'] != 'Braking (Alert)':
            car['alert'] = f"🚨 ATOA Alert: Accident at {int(accident_info['x'])}! Slowing down."
            car['status'] = 'Braking (Alert)'

        # --- 2. DRIVER VISUAL LOGIC (Normal Human Driving) ---
        car_in_front = cars[i-1] if i > 0 else None
        
        if car_in_front:
            distance = car_in_front['x'] - car['x']

            # A. Check for visual on the car in front
            if distance <= VISIBILITY_DISTANCE:
                # If the car in front is crashed...
                if car_in_front['status'] == 'Crashed':
                    # ...is it too late to stop?
                    if distance <= BRAKING_DISTANCE:
                        car['status'] = 'Crashed' # 💥 Chain reaction!
                        car['alert'] = "Too close to stop! CRASHED."
                    else:
                        # ...no, driver can see it and brake.
                        car['status'] = 'Braking (Visual)'
                        car['alert'] = "Driver View: Crash ahead! Braking."
                
                # If car in front is just braking, driver should also brake.
                elif car_in_front['status'].startswith('Braking'):
                    car['status'] = 'Braking (Visual)'
                    
            # B. If car is braking (from alert or visual), manage its speed
            if car['status'].startswith('Braking'):
                car['speed'] = BRAKING_SPEED
                # Logic to stop safely before the obstacle
                obstacle_x = accident_info['x'] if accident_info else (car_in_front['x'] if car_in_front else ROAD_LENGTH)
                if car['x'] >= (obstacle_x - BRAKING_DISTANCE - 5): # Stop 5 units behind
                    car['status'] = 'Stopped'
                    car['alert'] = "Stopped safely."
            
            # C. If no alerts and no visual, drive normally
            elif car['status'] == 'Normal':
                car['speed'] = NORMAL_SPEED
                # Simple follow logic to avoid bumping
                if distance < (BRAKING_DISTANCE + 5):
                    car['speed'] = BRAKING_SPEED


        # --- 3. Move the car ---
        car['x'] += car['speed']
        # Don't go off the road
        car['x'] = min(car['x'], ROAD_LENGTH)


def render_road(cars):
    """Creates a text-based string for the road."""
    road = ["-"] * ROAD_LENGTH
    for car in reversed(cars): # Draw back-to-front
        pos = int(car['x'])
        if 0 <= pos < ROAD_LENGTH:
            if car['status'] == 'Crashed':
                road[pos] = "💥"
            elif car['status'] == 'Stopped':
                road[pos] = "■" # Stopped car
            elif car['status'].startswith('Braking'):
                road[pos] = "B" # Braking car
            else:
                road[pos] = "▶" # Normal car
    return "".join(road)

# -----------------------
# INITIALIZE SESSION STATE
# -----------------------
if 'simulation_running' not in st.session_state:
    st.session_state.simulation_running = False

if run_button:
    st.session_state.road_1_cars = initialize_cars("A")
    st.session_state.road_2_cars = initialize_cars("B")
    st.session_state.road_2_accident = None # No accident on Road 2 yet
    st.session_state.simulation_running = True

# -----------------------
# MAIN SIMULATION LOOP
# -----------------------
if st.session_state.simulation_running:
    
    # --- 1. Check for a new RANDOM accident on Road 2 ---
    if not st.session_state.road_2_accident: # If no accident has happened yet
        lead_car_2 = st.session_state.road_2_cars[0]
        # Check if lead car is on the road and a random event triggers
        if lead_car_2['x'] < (ROAD_LENGTH - 10) and random.random() < ACCIDENT_PROBABILITY:
            lead_car_2['status'] = 'Crashed'
            st.session_state.road_2_accident = {'x': lead_car_2['x']}
            st.warning(f"💥 Accident Occurred on Road 2 at position {int(lead_car_2['x'])}!")
            st.info("ATOA System is broadcasting alert to other cars on Road 2...")

    # --- 2. Update logic for both roads ---
    # Road 1: No accident info is passed in
    update_road_logic(st.session_state.road_1_cars, None) 
    
    # Road 2: The accident info IS passed in
    update_road_logic(st.session_state.road_2_cars, st.session_state.road_2_accident)

    # --- 3. Render the simulation ---
    st.subheader("Road 1 (Control - No Alerts)")
    st.code(render_road(st.session_state.road_1_cars))
    
    st.subheader("Road 2 (ATOA Protected)")
    st.code(render_road(st.session_state.road_2_cars))

    # --- 4. Render info boxes ---
    st.markdown("---")
    st.markdown(f"**Fog Visibility:** {VISIBILITY_DISTANCE:.1f} units | **Safe Braking Distance:** {BRAKING_DISTANCE} units")
    cols = st.columns(num_cars)
    for i in range(num_cars):
        car1 = st.session_state.road_1_cars[i]
        car2 = st.session_state.road_2_cars[i]
        
        with cols[i]:
            st.text(f"Car {car1['id']}")
            st.metric(f"Status", car1['status'])
            
            st.text(f"Car {car2['id']}")
            st.metric(f"Status", car2['status'])
            if car2['alert']:
                st.info(car2['alert']) # Show the ATOA alert!

    # --- 5. Check end condition ---
    lead_car_1_stopped = st.session_state.road_1_cars[0]['x'] >= ROAD_LENGTH
    lead_car_2_stopped = st.session_state.road_2_cars[0]['x'] >= ROAD_LENGTH or st.session_state.road_2_cars[0]['status'] == 'Crashed'

    if lead_car_1_stopped and lead_car_2_stopped:
        st.session_state.simulation_running = False
        st.success("Simulation Finished.")
    else:
        # Rerun the script to create the animation loop
        time.sleep(0.3)
        st.rerun()
