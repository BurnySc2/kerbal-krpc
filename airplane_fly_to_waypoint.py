import time
import math
import krpc
from loguru import logger

from helper import surface_distance_to_vessel, calc_bearing, clip


conn = krpc.connect(name="Airplane fly to waypoint")
vessel = conn.space_center.active_vessel
nodes = vessel.control.nodes


# CONFIG
target_height = 5_000
min_height = 1_000
max_pitch_angle = 30


vessel_experiments = conn.add_stream(getattr, vessel.parts, "experiments")
vessel_surface_altitude = conn.add_stream(getattr, vessel.flight(), "surface_altitude")


current_target = None
while 1:
    time.sleep(1)
    # Get contract
    if not current_target:
        waypoints = conn.space_center.waypoint_manager.waypoints
        waypoints.sort(key=lambda w: surface_distance_to_vessel(w.latitude, w.longitude))
        current_target = next(
            (w for w in waypoints if w.has_contract and w.near_surface and w.surface_altitude < 15_000), None
        )
        if current_target:
            logger.info(
                f"Found a waypoint target: {current_target.name} with distance {surface_distance_to_vessel(current_target.latitude, current_target.longitude):.01f} in direction {calc_bearing(current_target.longitude, current_target.latitude):.01f}"
            )
            vessel.auto_pilot.engage()
            vessel.control.throttle = 1
            # vessel.auto_pilot.deceleration_time = (30, 30, 10)
            # vessel.auto_pilot.deceleration_time = (5, 5, 5)
            vessel.auto_pilot.deceleration_time = (10, 5, 5)
            vessel.auto_pilot.target_roll = 0

            vessel.auto_pilot.roll_threshold = 180
            vessel.auto_pilot.roll_threshold = 5
            vessel.auto_pilot.target_roll = 0

    if current_target:
        # vessel_horizontal_speed = flight.horizontal_speed

        # Auto correct bearing
        target_heading = calc_bearing(current_target.latitude, current_target.longitude)

        # Auto correct pitch based on altitude
        frac = (target_height - vessel_surface_altitude()) / (target_height - min_height)
        target_pitch = clip(-1, frac, 1) * max_pitch_angle
        # logger.info(f"Aiming for heading {target_heading} and pitch {target_pitch}")

        # vessel.auto_pilot.target_pitch_and_heading(target_pitch, target_heading)
        # vessel.auto_pilot.target_pitch = 10
        vessel.auto_pilot.target_pitch = target_pitch
        # vessel.auto_pilot.target_heading = 90
        vessel.auto_pilot.target_heading = target_heading
        # logger.info(f"Autopilot error: {vessel.auto_pilot.pitch_error}, {vessel.auto_pilot.heading_error}, {vessel.auto_pilot.roll_error}")

        # If close to target, run experiment
        distance_to_waypoint = surface_distance_to_vessel(current_target.latitude, current_target.longitude)
        experiments = vessel_experiments()
        if distance_to_waypoint < 1500:
            if current_target.icon == "report":
                experiment = next((e for e in experiments if "Cockpit" in e.part.name), None)
                if experiment:
                    if experiment.has_data:
                        experiment.reset()
                        time.sleep(0.1)
                    experiment.run()
                    logger.info(f"Gathering experiment in part {experiment.part.name} {current_target.icon}")
                    current_target = None
            # Mark1Cockpit
            # sensorBarometer
            # sensorThermometer
            # GooExperiment
            # science.module
            # MK1CrewCabin

    # If no more waypoint, exit program
    else:
        logger.info(f"Exiting program. No more waypoints available")
        # vessel.control.throttle = 0
        vessel.auto_pilot.disengage()
