import time
import krpc
from loguru import logger

conn = krpc.connect(name="Airplane test")
vessel = conn.space_center.active_vessel
nodes = vessel.control.nodes

# CONFIG
target_height = 5_000
min_height = 1000
max_pitch_angle = 30


vessel.auto_pilot.engage()
vessel.auto_pilot.target_roll = 0

# Default values
vessel.auto_pilot.deceleration_time = (5, 5, 5)
vessel.auto_pilot.roll_threshold = 5

# Very slow turning, good for big planes
vessel.auto_pilot.deceleration_time = (10, 30, 30)

# Roll threshold of 180 makes the plane not use any roll, threshold of 90 still makes the plane roll if the bearing difference angle is bigger than 90
# If the bearing difference angle is bigger than threshold, then the airplane starts to roll to get to that bearing, so set it to 180 if the airplane should never use roll
# vessel.auto_pilot.roll_threshold = 180

logger.info(f"{vessel.auto_pilot.deceleration_time}")
logger.info(f"{vessel.auto_pilot.roll_threshold}")

while 1:
    time.sleep(0.1)
    vessel.auto_pilot.target_pitch = 5
    vessel.auto_pilot.target_heading = 90
