import time
import krpc
from loguru import logger

conn = krpc.connect(name="Sub-orbital flight")
vessel = conn.space_center.active_vessel

# vessel.auto_pilot.target_pitch_and_heading(90, 90)
# vessel.auto_pilot.engage()
# vessel.control.throttle = 1
#
#
# stage = vessel.control.current_stage
# resources = vessel.resources_in_decouple_stage(stage - 1)
# solid_fuel_amount: float = resources.amount("SolidFuel")
# liquid_fuel_amount: float = resources.amount("LiquidFuel")

altitude = conn.add_stream(getattr, vessel.flight(), "mean_altitude")
t0 = time.perf_counter_ns()
mean_altitude = altitude()
t1 = time.perf_counter_ns()

logger.info(f"Time for Altitude from stream: {t1-t0}")

t0 = time.perf_counter_ns()
mean_altitude = vessel.flight().mean_altitude
t1 = time.perf_counter_ns()
logger.info(f"Time for Altitude from idk: {t1-t0}")
