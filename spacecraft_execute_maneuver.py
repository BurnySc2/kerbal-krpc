import time
import math
import krpc
from loguru import logger
from helper import stage_if_low_on_fuel

conn = krpc.connect(name="Create orbit")
vessel = conn.space_center.active_vessel
# waypoints = conn.space_center.waypoint_manager
nodes = vessel.control.nodes

# CONFIG
burn_till_remaining_delta_v = 20
# 20 seconds buffer when warping to node
warp_to_buffer_seconds = 20
# Degree tolerance at burn
tolerance_tuple = (0.05, 0.05, 0.05)

if not nodes:
    logger.info(f"No maneuver node found. Exiting program")
    exit()
n = nodes[0]

# Stage if no ISP available
# if isp not available: stage until we get something with fuel
while not vessel.specific_impulse or not vessel.available_thrust:
    stage_if_low_on_fuel()
    time.sleep(0.5)


vessel.auto_pilot.reference_frame = n.reference_frame
vessel.auto_pilot.target_direction = (0, 1, 0)
vessel.auto_pilot.engage()

# TODO what to do when remaining fuel is not enough? burn time is wrongly calculated then
delta_v = n.delta_v
F = vessel.available_thrust
Isp = vessel.specific_impulse * 9.82
m0 = vessel.mass
m1 = m0 / math.exp(delta_v / Isp)
flow_rate = F / Isp
burn_time = (m0 - m1) / flow_rate

burn_start_time = lambda: n.time_to - burn_time / 2

# Warp to 20 seconds before burn
logger.info(f"Warping to node ({warp_to_buffer_seconds} seconds before maneuver starts)")
warp_time = conn.space_center.ut + burn_start_time() - warp_to_buffer_seconds
conn.space_center.warp_to(warp_time)

# Waiting till burn start time
while burn_start_time() > 1.2:
    d = vessel.flight(n.reference_frame).direction
    a = (0, 1, 0)
    spacecraft_facing_direction: bool = all(abs(d[i] - a[i]) < tolerance_tuple[i] for i in range(3))
    # burn_start_time = n.time_to - burn_time/2
    logger.info(f"Ready: {spacecraft_facing_direction}, maneuver starting in {int(burn_start_time())}...")
    # logger.info(f", facing direction: {d}")
    time.sleep(1)
while burn_start_time() > 0.1:
    time.sleep(0.05)

node_remaining_delta_v = conn.add_stream(getattr, n, "remaining_delta_v")

flight = vessel.flight(n.reference_frame)
d = flight.direction
a = (0, 1, 0)
spacecraft_facing_direction: bool = all(abs(d[i] - a[i]) < tolerance_tuple[i] for i in range(3))

last_node_remaining_delta_v = math.inf
fine_tuning = False
tolerance_timer = 1
step_time = 0.01

if spacecraft_facing_direction:
    logger.info(f"Starting maneuver burn.")

    while 1:
        remaining_delta_v = node_remaining_delta_v()
        tolerance_timer -= step_time

        if remaining_delta_v > last_node_remaining_delta_v and tolerance_timer < 0:
            logger.warning(f"Something went wrong: remaining burn delta v went up! Ending program. Remaining delta v: {remaining_delta_v}")
            n.remove()
            break

        elif remaining_delta_v > burn_till_remaining_delta_v:
            vessel.control.throttle = 1

        elif remaining_delta_v > 0.0001:
            vessel.control.throttle = remaining_delta_v / burn_till_remaining_delta_v
            if not fine_tuning:
                logger.info(f"Maneuver almost done. Fine tuning.")
                fine_tuning = True

        elif remaining_delta_v < 0.0001:
            logger.info(f"Maneuver completed. Ending program. Remaining delta v: {remaining_delta_v}")
            n.remove()
            break

        stage_if_low_on_fuel()
        last_node_remaining_delta_v = remaining_delta_v
        time.sleep(step_time)
else:
    logger.info(
        f"Spacecraft was not facing in the correct direction. Direction: {d}, tolerance tuple: {tolerance_tuple}"
    )


vessel.control.throttle = 0
vessel.auto_pilot.disengage()
