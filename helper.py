import time
import math
import krpc
from loguru import logger

conn = krpc.connect(name="Helper")

vessel = conn.space_center.active_vessel

vessel_current_stage = conn.add_stream(getattr, vessel.control, "current_stage")


def stage_if_low_on_fuel(do_stage=True) -> float:
    stage = vessel_current_stage()
    resources = vessel.resources_in_decouple_stage(stage - 1)
    solid_fuel_amount: float = resources.amount("SolidFuel")
    liquid_fuel_amount: float = resources.amount("LiquidFuel")

    # resources_next = vessel.resources_in_decouple_stage(stage - 2, cumulative=True)
    # next_stage_solid_fuel_amount: float = resources_next.amount("SolidFuel")
    # next_stage_liquid_fuel_amount: float = resources_next.amount("LiquidFuel")

    # logger.info(f"Current stage vs next sage: Solid fuel {solid_fuel_amount:.01f} / {next_stage_solid_fuel_amount:.01f}, liquid fuel {liquid_fuel_amount:.01f} / {next_stage_liquid_fuel_amount:.01f}")

    if solid_fuel_amount < 0.1 and liquid_fuel_amount < 0.1:
        if do_stage:
            logger.info(
                f"Staging because solid fuel is at {solid_fuel_amount} and liquid fuel at {liquid_fuel_amount}! Current stage is {stage}"
            )
            vessel.control.activate_next_stage()
        return 0
    return max(solid_fuel_amount, liquid_fuel_amount)


vessel_thrust = conn.add_stream(getattr, vessel, "thrust")


def airplane_stage():
    thrust = vessel_thrust()
    if thrust < 0.1:
        logger.info(f"Staging airplane!")
        vessel.control.activate_next_stage()


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


vessel_latitude = conn.add_stream(getattr, vessel.flight(), "latitude")
vessel_longitude = conn.add_stream(getattr, vessel.flight(), "longitude")


def calc_bearing(latitude: float, longitude: float):
    f_longitude = vessel_longitude()
    f_latitude = vessel_latitude()
    lat1 = math.radians(f_latitude)
    lat2 = math.radians(latitude)
    long1 = math.radians(f_longitude)
    long2 = math.radians(longitude)
    y = math.sin(long2 - long1) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(long2 - long1)
    bearing = math.degrees(math.atan2(y, x))
    return bearing % 360


def surface_distance_to_vessel(latitude: float, longitude: float) -> float:
    # Kerbin radius in meters
    R = 600_000
    flight = vessel.flight()
    f_longitude = vessel_longitude()
    f_latitude = vessel_latitude()
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


def clip(minn: float, value: float, maxx: float) -> float:
    return max(minn, min(value, maxx))


if __name__ == "__main__":
    while 1:
        stage_if_low_on_fuel()
        time.sleep(1)
