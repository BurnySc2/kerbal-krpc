import time
import krpc
from loguru import logger
from helper import stage_if_low_on_fuel

conn = krpc.connect(name="Sub-orbital flight")
vessel = conn.space_center.active_vessel

# CONFIG
target_apoapasis_altitude = 72_000
gravity_turn_start_altitude = 5_000
gravity_turn_end_altitude = 60_000
min_altitude_before_program_stops = 35_000
boost_until_out_of_fuel = True

# Degree tolerance
pitch_tolerance = 5
heading_tolerance = 10
# END OF CONFIG

# while vessel.situation.name not in {"pre_launch"}:
#     logger.info(f"Vessel not in 'pre_launch' phase!")
#     time.sleep(3)

vessel.auto_pilot.engage()
vessel.auto_pilot.target_pitch = 90
vessel.auto_pilot.target_heading = 90
vessel.auto_pilot.roll_threshold = 5
vessel.auto_pilot.target_roll = 0

# Create connection streams, about 20 times faster than just calling them directly
vessel_surface_altitude = conn.add_stream(getattr, vessel.flight(), "surface_altitude")
vessel_apoapsis_altitude = conn.add_stream(getattr, vessel.orbit, "apoapsis_altitude")
vessel_pitch = conn.add_stream(getattr, vessel.flight(), "pitch")
vessel_heading = conn.add_stream(getattr, vessel.flight(), "heading")

if vessel_surface_altitude() < 1_000:
    vessel.control.throttle = 1

time.sleep(1)
apoapsis_reached_once = False

while 1:
    time.sleep(0.01)

    apoapsis_altitude = vessel_apoapsis_altitude()
    if apoapsis_altitude < target_apoapasis_altitude:
        stage_if_low_on_fuel()

    # Start Gravity turn
    surface_altitude = vessel_surface_altitude()

    target_pitch, target_heading = vessel.auto_pilot.target_pitch, vessel.auto_pilot.target_heading

    pitch_tolerance_temp = pitch_tolerance
    if boost_until_out_of_fuel and (
        surface_altitude > 20_000 and apoapsis_altitude > target_apoapasis_altitude or apoapsis_reached_once
    ):
        # logger.info(f"Going for 0 pitch, altitude {surface_altitude}, apoapsis {apoapsis_altitude}")
        apoapsis_reached_once = True
        target_pitch = 0
        if apoapsis_altitude < target_apoapasis_altitude:
            pitch_tolerance_temp = 30

    elif surface_altitude > gravity_turn_start_altitude:
        frac = (surface_altitude - gravity_turn_start_altitude) / (
            gravity_turn_end_altitude - gravity_turn_start_altitude
        )
        target_pitch = 90 - min(90, frac * 90)
        # logger.info(f"Altitude {mean_altitude}, aiming for pitch: {target_pitch}")

    # If spacecraft is not facing the target pitch and heading: throttle down
    current_pitch = vessel_pitch()
    current_heading = vessel_heading()
    vessel_facing_target = (
        abs(target_pitch - current_pitch) < pitch_tolerance_temp
        and abs(target_heading - current_heading) < heading_tolerance
    )
    # Only if pitch is <90 can the heading be facing the correct way
    if not vessel_facing_target and target_pitch < 90:
        vessel.control.throttle -= 0.10
        # logger.info(
        #     f"Vessel not facing the right way, lowering throttle:\nPitch: {current_pitch} / {target_pitch}, Heading: {current_heading} / {target_heading}"
        # )
    else:
        vessel.control.throttle += 0.03

    vessel.auto_pilot.target_pitch = target_pitch

    if boost_until_out_of_fuel and stage_if_low_on_fuel(do_stage=False) > 0.1:
        pass
    # If apoapsis reached, end program
    elif (
        min_altitude_before_program_stops < vessel_surface_altitude() and target_apoapasis_altitude < apoapsis_altitude
    ):
        logger.info(
            f"Apoapsis of {apoapsis_altitude:.01f} and min altitude of {vessel_surface_altitude():.01f} reached. Ending program."
        )
        break

vessel.control.throttle = 0
vessel.auto_pilot.disengage()
vessel.control.sas = True
vessel.auto_pilot.roll_threshold = 5
print(vessel.control.sas_mode)
# vessel.control.sas_mode = "stability_assist"
