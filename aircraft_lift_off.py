import time
import math
import krpc
from loguru import logger

from helper import airplane_stage, surface_distance_to_vessel, clip

conn = krpc.connect(name="Aircraft lift off")
vessel = conn.space_center.active_vessel


# CONFIG
target_height = 5_000
min_height = 1_000
max_pitch_angle = 30
# in m/s
lift_off_velocity = 50
# in meters
snapshot_distance_interval = 1000
total_snapshots = 10
# The airway field is 2km long

obt_frame = vessel.orbit.body.non_rotating_reference_frame
srf_frame = vessel.orbit.body.reference_frame

obt_speed = vessel.flight(obt_frame).speed
srf_speed = vessel.flight(srf_frame).speed

vessel_experiments = conn.add_stream(getattr, vessel.parts, "experiments")
vessel_surface_altitude = conn.add_stream(getattr, vessel.flight(), "surface_altitude")
vessel_vertical_speed = conn.add_stream(getattr, vessel.flight(srf_frame), "vertical_speed")
vessel_horizontal_speed = conn.add_stream(getattr, vessel.flight(srf_frame), "horizontal_speed")
vessel_surface_speed = conn.add_stream(getattr, vessel.flight(srf_frame), "speed")
vessel_pitch = conn.add_stream(getattr, vessel.flight(), "pitch")
vessel_heading = conn.add_stream(getattr, vessel.flight(), "heading")


vessel.auto_pilot.engage()
vessel.control.throttle = 1
vessel.control.brakes = False

vessel.auto_pilot.roll_threshold = 180
vessel.auto_pilot.deceleration_time = (30, 30, 30)
# vessel.auto_pilot.deceleration_time = (5, 5, 5)
vessel.auto_pilot.attenuation_angle = (0.1, 0.1, 0.1)

vessel.auto_pilot.target_roll = 0
vessel.auto_pilot.target_heading = 90

vessel_latitude = conn.add_stream(getattr, vessel.flight(), "latitude")
vessel_longitude = conn.add_stream(getattr, vessel.flight(), "longitude")

start_pos = (vessel_latitude(), vessel_longitude())
logger.info(f"Noting start position: {start_pos}")
approach_positions = []

while 1:
    time.sleep(0.1)

    airplane_stage()

    if vessel_surface_speed() < lift_off_velocity and vessel_surface_altitude() < 100:
        # logger.info(
        #     f"Not reached enough velocity yet, accelerating on ground {vessel_surface_speed()} < {lift_off_velocity}!"
        # )
        vessel.auto_pilot.target_pitch = vessel_pitch()

    else:
        distance_to_start = surface_distance_to_vessel(start_pos[0], start_pos[1])
        if (
            distance_to_start > snapshot_distance_interval * (len(approach_positions) + 1)
            and len(approach_positions) < total_snapshots
        ):
            approach_positions.append((vessel_latitude(), vessel_longitude()))
            logger.info(
                f"Noting approach position ({len(approach_positions)}): {distance_to_start:.02f} - {approach_positions[-1]}"
            )
            if len(approach_positions) == total_snapshots:
                print("[")
                for i in approach_positions:
                    print("\t", i, end=",\n")
                print("]")
        # Auto correct pitch based on altitude
        frac = (target_height - vessel_surface_altitude()) / (target_height - min_height)
        target_pitch = clip(-1, frac, 1) * max_pitch_angle

        vessel.auto_pilot.target_pitch = target_pitch
        logger.info(f"Reached enough horizontal velocity, take off! Target pitch: {target_pitch}")

    # logger.info(f"{vessel.situation.name}")
    # if vessel.situation.name in {"landed", "splashed"}:
    #     break
