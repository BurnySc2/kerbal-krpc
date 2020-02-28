import time
import math
import krpc
from loguru import logger

conn = krpc.connect(name="Create orbit")
vessel = conn.space_center.active_vessel
# waypoints = conn.space_center.waypoint_manager
nodes = vessel.control.nodes

# CONFIG
burn_till_remaining_delta_v = 10
burn_till_remaining_delta_v_fine_tune = 0.1
# 20 seconds buffer when warping to node
warp_to_buffer_seconds = 20

if not nodes:
    logger.info(f"No maneuver node found. Exiting program")

n = nodes[0]

# Degree tolerance
tolerance_tuple = (0.01, 0.005, 0.01)

# while vessel.situation.name not in {"pre_launch"}:
#     logger.info(f"Vessel not in 'pre_launch' phase!")
#     time.sleep(3)

vessel.auto_pilot.reference_frame = n.reference_frame
vessel.auto_pilot.target_direction = (0, 1, 0)
vessel.auto_pilot.engage()

# TODO if isp not available: stage until we get something with fuel
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

flight = vessel.flight(n.reference_frame)
d = flight.direction
a = (0, 1, 0)
spacecraft_facing_direction: bool = all(abs(d[i] - a[i]) < tolerance_tuple[i] for i in range(3))


def stage_if_low_on_fuel():
    stage = vessel.control.current_stage
    resources = vessel.resources_in_decouple_stage(stage - 1)
    solid_fuel_amount: float = resources.amount("SolidFuel")
    liquid_fuel_amount: float = resources.amount("LiquidFuel")

    if solid_fuel_amount < 0.1 and liquid_fuel_amount < 0.1:
        logger.info(f"Staging! Current stage is {stage}")
        vessel.control.activate_next_stage()


node_remaining_delta_v = conn.add_stream(getattr, n, "remaining_delta_v")

if spacecraft_facing_direction:
    logger.info(f"Starting maneuver burn.")
    n_remaining_delta_v = node_remaining_delta_v()
    vessel.control.throttle = 1

    while n_remaining_delta_v > burn_till_remaining_delta_v:
        stage_if_low_on_fuel()
        time.sleep(0.01)
    vessel.control.throttle = 0.1
    logger.info(f"Maneuver almost done. Fine tuning.")

    while n_remaining_delta_v > burn_till_remaining_delta_v_fine_tune:
        stage_if_low_on_fuel()
        time.sleep(0.01)
    vessel.control.throttle = 0
    vessel.auto_pilot.disengage()
    logger.info(f"Maneuver completed. Ending program.")
else:
    logger.info(
        f"Spacecraft was not facing in the correct direction. Direction: {d}, tolerance tuple: {tolerance_tuple}"
    )
