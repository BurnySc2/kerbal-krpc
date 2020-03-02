import time
import math
import krpc
from loguru import logger

from helper import airplane_stage, surface_distance_to_vessel, calc_bearing, clip

conn = krpc.connect(name="Aircraft lift off")
vessel = conn.space_center.active_vessel


# CONFIG
# Max height before approaching the landing strip
max_height = 2_000
max_pitch_angle = 30
# in m/s
land_horizontal_velocity = 50
# Velocity before approaching landing strip
max_horizontal_velocity = 200
# in m/s^2
max_horizontal_acceleration = 5
full_speed_until_distance_from_stop = 8_000


# List should be approached in reverse
approach_positions = [
    (-0.04890819975806609, -74.61715594392183),
    (-0.04903254063985847, -74.52202945586112),
    (-0.04888744349362171, -74.4262874262937),
    # (-0.048610370996377016, -74.33118874491561),
    (-0.04823103686423749, -74.23520377127176),
    # (-0.0477959568040884, -74.13928068856688),
    (-0.0473724048307247, -74.04486868365854),
    # (-0.04696806021551466, -73.94921178031439),
    # (-0.0465586749007686, -73.85183988928668),
    (-0.046139842471566, -73.75689623484516),
]
approach_index = len(approach_positions) - 1

# The position where the plane should stop at
stop_position = (-0.04854783753949805, -74.71340562868204)


srf_frame = vessel.orbit.body.reference_frame

vessel_vertical_speed = conn.add_stream(getattr, vessel.flight(srf_frame), "vertical_speed")
vessel_horizontal_speed = conn.add_stream(getattr, vessel.flight(srf_frame), "horizontal_speed")
vessel_surface_speed = conn.add_stream(getattr, vessel.flight(srf_frame), "speed")
vessel_latitude = conn.add_stream(getattr, vessel.flight(), "latitude")
vessel_longitude = conn.add_stream(getattr, vessel.flight(), "longitude")
vessel_g_force = conn.add_stream(getattr, vessel.flight(), "g_force")
vessel_surface_altitude = conn.add_stream(getattr, vessel.flight(), "surface_altitude")
vessel_aerodynamic_force = conn.add_stream(getattr, vessel.flight(), "aerodynamic_force")
vessel_pitch = conn.add_stream(getattr, vessel.flight(), "pitch")
vessel_heading = conn.add_stream(getattr, vessel.flight(), "heading")


vessel.auto_pilot.engage()
# # vessel.control.throttle = 1

vessel.auto_pilot.roll_threshold = 5
# vessel.auto_pilot.roll_threshold = 20

# vessel.auto_pilot.deceleration_time = (30, 30, 10)
vessel.auto_pilot.deceleration_time = (5, 5, 5)
# vessel.auto_pilot.deceleration_time = (10, 5, 5)

# Try to aim as best as possible
vessel.auto_pilot.attenuation_angle = (0.1, 0.1, 0.1)

vessel.auto_pilot.target_roll = 0
# # vessel.auto_pilot.target_heading = 90


vertical_velocity_old = vessel_vertical_speed()
vertical_velocity_current = vessel_vertical_speed()

horizontal_velocity_old = vessel_horizontal_speed()
horizontal_velocity_current = vessel_horizontal_speed()

target_pitch = vessel_pitch()
time_interval = 0.1
touch_down = False
while 1:
    time.sleep(time_interval)

    brakes = False
    # airplane_stage()

    target_position: tuple = approach_positions[approach_index] if approach_index >= 0 else stop_position
    distance_to_target: float = surface_distance_to_vessel(*target_position)
    distance_to_stop: float = surface_distance_to_vessel(*stop_position)

    # Vertical acceleration in m/s^2
    vertical_velocity_old = vertical_velocity_current
    vertical_velocity_current = vessel_vertical_speed()
    vertical_acceleration = (vertical_velocity_current - vertical_velocity_old) / time_interval

    # Horizontal acceleration in m/s^2
    horizontal_velocity_old = horizontal_velocity_current
    horizontal_velocity_current = vessel_horizontal_speed()
    horizontal_acceleration = (horizontal_velocity_current - horizontal_velocity_old) / time_interval

    # Velocity and acceleration as fraction compared to target max velocity and acceleration
    if distance_to_stop < full_speed_until_distance_from_stop:
        horizontal_velocity_fraction = horizontal_velocity_current / land_horizontal_velocity
    else:
        horizontal_velocity_fraction = horizontal_velocity_current / max_horizontal_velocity
    horizontal_acceleration_fraction = horizontal_acceleration / max_horizontal_acceleration
    # Increase throttle if horizontal velocity is below landing velocity
    if horizontal_velocity_fraction < 1:
        # Max acceleration not yet reached
        if horizontal_acceleration < 1:
            if vessel.control.throttle < 1:
                logger.info(f"Increasing throttle")
            vessel.control.throttle += 0.05
        else:
            pass
    # Lower throttle if horizontal velocity is above landing velocity
    else:
        # Max decceleration not yet reached
        if horizontal_acceleration > -1:
            if vessel.control.throttle > 0:
                logger.info(f"Lowering throttle")
            vessel.control.throttle -= 0.1
        else:
            pass

        if horizontal_velocity_fraction > 1.1:
            brakes = True

    target_altitude = (distance_to_stop - 1800) / 10
    target_altitude = clip(0.01, target_altitude, max_height)

    # TODO figure out at what pitch there is very little altitude loss at current velocity
    replace_me_pitch = 1
    # TODO also figure out how far the wheels are away from the center of mass
    replace_me_altitude = 20
    if target_altitude > replace_me_altitude and not touch_down:
        frac1 = 1 - vessel_surface_altitude() / target_altitude
        frac2 = target_altitude / vessel_surface_altitude() - 1
        frac = frac1 if vessel_surface_altitude() >= target_altitude else frac2
        angle = 0.5 * clip(-math.pi, frac, math.pi)
        target_pitch = math.sin(angle) * max_pitch_angle

        target_pitch = clip(-max_pitch_angle, target_pitch, max_pitch_angle)
        logger.info(
            f"Target pitch: {target_pitch:.01f}, target height: {target_altitude:.01f}, {angle:.01f} {frac:.01f} {distance_to_stop:.01f}"
        )
        vessel.auto_pilot.target_pitch = target_pitch

        # Calculate heading (bearing) to target coordinate
        target_heading: float = calc_bearing(*target_position)
        vessel.auto_pilot.target_heading = target_heading
    else:
        touch_down = True
        vessel.auto_pilot.target_pitch = replace_me_pitch
        vessel.auto_pilot.target_heading = 270
        vessel.control.throttle = 0
        brakes = True


    vessel.control.brakes = brakes

    # If close to waypoint, pick next waypoint
    if distance_to_target < min(2000, 5*max_horizontal_velocity) and target_position != stop_position:
        approach_index -= 1
        logger.info(f"Reached a waypoint! Approach index at: {approach_index}")

    # If horizontal speed small 1 and low altitude, means we landed probably
    if vessel_horizontal_speed() < 1 and vessel_surface_altitude() < 100:
        time.sleep(1)
        logger.info(f"Aircraft landed (I hope)!")
        break

# vessel.control.brakes = False
vessel.control.throttle = 0
vessel.auto_pilot.disengage()
# Reset autopilot values
vessel.auto_pilot.attenuation_angle = (1, 1, 1)
