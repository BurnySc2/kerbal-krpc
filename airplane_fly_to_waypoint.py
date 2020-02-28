import time
import math
import krpc
from loguru import logger

conn = krpc.connect(name="Create orbit")
vessel = conn.space_center.active_vessel
nodes = vessel.control.nodes


# CONFIG
target_height = 5_000
min_height = 1000
max_pitch_angle = 30


def calcDistance(lat1, lon1, lat2, lon2, bodyRadius=1):
    if bodyRadius == 1:
        bodyRadius = vessel.orbit.body.equatorial_radius
    # convert input degrees to radians
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    d = math.acos(math.sin(lat1) * math.sin(lat2) + math.cos(lat1) * math.cos(lat2) * math.cos(lon1 - lon2))
    return d * bodyRadius


def calcBearing(lat1, lon1, lat2, lon2, d=-1):
    # convert input degrees to radians
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    dLon = lon2 - lon1

    y = math.sin(dLon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dLon)

    brng = math.atan2(y, x)

    brng = math.degrees(brng)
    brng = brng % 360
    # brng = 360 - brng # count degrees counter-clockwise - remove to make clockwise

    # 0° means north
    # 90° means east
    return brng


def calc_bearing(longitude: float, latitude: float):
    flight = vessel.flight()
    f_latitude = flight.latitude
    f_longitude = flight.longitude
    lat1 = math.radians(f_latitude)
    lat2 = math.radians(latitude)
    long1 = math.radians(f_longitude)
    long2 = math.radians(longitude)
    y = math.sin(long2 - long1) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(long2 - long1)
    bearing = math.degrees(math.atan2(y, x))
    return bearing % 360


def surface_distance_to_vessel(longitude: float, latitude: float) -> float:
    # Kerbin radius in meters
    R = 600_000
    flight = vessel.flight()
    f_longitude = flight.longitude
    f_latitude = flight.latitude
    lon1 = math.radians(f_longitude)
    lat1 = math.radians(f_latitude)
    lon2 = math.radians(longitude)
    lat2 = math.radians(latitude)
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    return distance


def clip(minn, value, maxx):
    return max(minn, min(value, maxx))


current_target = None
while 1:
    time.sleep(1)
    # Get contract
    if not current_target:
        waypoints = conn.space_center.waypoint_manager.waypoints
        waypoints.sort(key=lambda w: surface_distance_to_vessel(w.longitude, w.latitude))
        current_target = next(
            (w for w in waypoints if w.has_contract and w.near_surface and w.bedrock_altitude < 15_000), None
        )
        if current_target:
            logger.info(
                f"Found a waypoint target: {current_target.name} with distance {surface_distance_to_vessel(current_target.longitude, current_target.latitude):.01f} in direction {calc_bearing(current_target.longitude, current_target.latitude):.01f}"
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
        flight = vessel.flight()
        vessel_surface_height = flight.bedrock_altitude
        # vessel_horizontal_speed = flight.horizontal_speed

        # Auto correct bearing
        target_heading = calc_bearing(current_target.longitude, current_target.latitude)

        # Auto correct pitch based on altitude
        frac = (target_height - vessel_surface_height) / (target_height - min_height)
        target_pitch = clip(-1, frac, 1) * max_pitch_angle
        # logger.info(f"Aiming for heading {target_heading} and pitch {target_pitch}")

        # vessel.auto_pilot.target_pitch_and_heading(target_pitch, target_heading)
        # vessel.auto_pilot.target_pitch = 10
        vessel.auto_pilot.target_pitch = target_pitch
        # vessel.auto_pilot.target_heading = 90
        vessel.auto_pilot.target_heading = target_heading
        # logger.info(f"Autopilot error: {vessel.auto_pilot.pitch_error}, {vessel.auto_pilot.heading_error}, {vessel.auto_pilot.roll_error}")

        # If close to target, run experiment
        distance_to_waypoint = surface_distance_to_vessel(current_target.longitude, current_target.latitude)
        experiments = vessel.parts.experiments
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
