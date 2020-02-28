import time
import krpc
from loguru import logger

conn = krpc.connect(name="Sub-orbital flight")
vessel = conn.space_center.active_vessel

altitude = conn.add_stream(getattr, vessel.flight(), "mean_altitude")
vessel_current_stage = conn.add_stream(getattr, vessel.control, "current_stage")

t0 = time.perf_counter_ns()
# mean_altitude = altitude()
stage = vessel_current_stage()
t1 = time.perf_counter_ns()

logger.info(f"Time for Altitude from stream: {t1-t0}")

t0 = time.perf_counter_ns()
# mean_altitude = vessel.flight().mean_altitude
stage = vessel.control.current_stage
t1 = time.perf_counter_ns()
logger.info(f"Time for Altitude from idk: {t1-t0}")
