import time
import krpc
from loguru import logger
from helper import stage_if_low_on_fuel

conn = krpc.connect(name="Sub-orbital flight")
vessel = conn.space_center.active_vessel

# CONFIG
target_apoapasis_altitude = 100_000
gravity_turn_start_altitude = 10_000
gravity_turn_end_altitude = 60_000

# Degree tolerance
pitch_tolerance = 5
heading_tolerance = 10
# END OF CONFIG

# while vessel.situation.name not in {"pre_launch"}:
#     logger.info(f"Vessel not in 'pre_launch' phase!")
#     time.sleep(3)

vessel.auto_pilot.target_pitch_and_heading(90, 90)
vessel.auto_pilot.engage()
vessel.control.throttle = 1

# Create connection streams, about 20 times faster than just calling them directly
vessel_mean_altitude = conn.add_stream(getattr, vessel.flight(), "mean_altitude")
vessel_apoapsis_altitude = conn.add_stream(getattr, vessel.orbit, "apoapsis_altitude")
vessel_pitch = conn.add_stream(getattr, vessel.flight(), "pitch")
vessel_heading = conn.add_stream(getattr, vessel.flight(), "heading")


while 1:
    time.sleep(0.01)

    airplane_stage_if_low_on_fuel()

    # Start Gravity turn
    mean_altitude = vessel_mean_altitude()
    if mean_altitude > gravity_turn_start_altitude:
        frac = (mean_altitude - gravity_turn_start_altitude) / (gravity_turn_end_altitude - gravity_turn_start_altitude)
        target_pitch = 90 - min(90, frac * 90)
        vessel.auto_pilot.target_pitch = target_pitch
        # logger.info(f"Altitude {mean_altitude}, aiming for pitch: {target_pitch}")
    target_pitch, target_heading = vessel.auto_pilot.target_pitch, vessel.auto_pilot.target_heading

    # If spacecraft is not facing the target pitch and heading: throttle down
    current_pitch = vessel_pitch()
    current_heading = vessel_heading()
    vessel_facing_target = (
        abs(target_pitch - current_pitch) < pitch_tolerance
        and abs(target_heading - current_heading) < heading_tolerance
    )
    # Only if pitch is <90 can the heading be facing the correct way
    if not vessel_facing_target and target_pitch < 90:
        vessel.control.throttle -= 0.2
        # logger.info(
        #     f"Vessel not facing the right way, lowering throttle:\nPitch: {current_pitch} / {target_pitch}, Heading: {current_heading} / {target_heading}"
        # )
    else:
        vessel.control.throttle += 0.03

    # If apoapsis reached, end program
    apoapsis_altitude = vessel.orbit.apoapsis_altitude
    if apoapsis_altitude > vessel_apoapsis_altitude():
        logger.info(f"Apoapsis of {apoapsis_altitude} reached. Ending program.")
        vessel.control.throttle = 0
        vessel.auto_pilot.disengage()
        break
