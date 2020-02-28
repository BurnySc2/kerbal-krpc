import krpc
import time
from loguru import logger
from typing import Set

conn = krpc.connect(name="Run science experiments to gather science")
# How much science at least should be gathered if the experiment is run
min_science: float = 5
# How much percentage value the experiment has, e.g. if the experiment was already run 3 times, its probably gonna be under 0.1
min_scientific_value: float = 0.01


vessel = conn.space_center.active_vessel

obt_frame = vessel.orbit.body.non_rotating_reference_frame
srf_frame = vessel.orbit.body.reference_frame

obt_speed = vessel.flight(obt_frame).speed
srf_speed = vessel.flight(srf_frame).speed

while vessel.situation.name in {"pre_launch"}:
    time.sleep(0.1)

logger.info(f"Gathering science...")
while 1:
    time.sleep(2)
    names_run: Set[str] = set()
    parts = vessel.parts
    experiments = parts.experiments
    for i, experiment in enumerate(experiments):
        name: str = experiment.part.name
        if experiment.inoperable or not experiment.available:
            continue
        if name in names_run:
            continue

        scientific_value = science_cap = science = 0
        if experiment.science_subject is not None:
            # A value between 0 and 1
            scientific_value: float = experiment.science_subject.scientific_value
            # How much science can be gathered total?
            science_cap: float = experiment.science_subject.science_cap
            # Science that can be obtained if ran
            science: float = scientific_value * science_cap

        # Currently stored science
        current_science_value: float = 0 if not experiment.has_data else experiment.data[0].science_value
        if not experiment.has_data and current_science_value == 0:
            if science >= min_science and scientific_value > min_scientific_value:
                logger.info(
                    f"{i}: Running experiment on part: {experiment.part.name} to obtain {science:.2f} science ({scientific_value:.2f} scientific value)"
                )
                experiment.run()
                names_run.add(name)
        elif experiment.has_data and experiment.rerunnable and current_science_value < science:
            if science >= min_science and scientific_value > min_scientific_value:
                experiment.reset()
                time.sleep(0.1)
                logger.info(
                    f"{i}: Re-running experiment on part: {experiment.part.name} to obtain {science:.2f} science ({scientific_value:.2f} scientific value) and discarding old value of {current_science_value:.2f} science"
                )
                experiment.run()
                names_run.add(name)

    # https://krpc.github.io/krpc/python/api/space-center/vessel.html#SpaceCenter.VesselSituation
    if vessel.situation.name in {"landed", "splashed"}:
        break
    # if vessel.flight(srf_frame).speed < 0.1:
    #     break


logger.info(vessel.name)
logger.info("END OF PROGRAM")

# vessel.auto_pilot.target_pitch_and_heading(90, 90)
# vessel.auto_pilot.engage()
# vessel.control.throttle = 1
# time.sleep(1)

# print('Launch!')
# vessel.control.activate_next_stage()
