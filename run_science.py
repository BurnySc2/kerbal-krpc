import krpc
import time
from loguru import logger
from typing import Set

conn = krpc.connect(name="Run science experiments to gather science")
vessel = conn.space_center.active_vessel

# Create connection streams, about 20 times faster than just calling them directly
vessel_experiments = conn.add_stream(getattr, vessel.parts, "experiments")


class Science:
    def __init__(self):
        # How much science at least should be gathered if the experiment is run
        self.min_science: float = 0.01
        # self.min_science: float = 5
        # How much percentage value the experiment has, e.g. if the experiment was already run 3 times, its probably gonna be under 0.1
        self.min_scientific_value: float = 0.01
        # Only automatically run experiments that can be rerun
        self.run_non_rerunnable_science = False
        # TODO Automatically transmit if we have enough electric charge to transmit data ?
        self.transmit_science = False
        self.min_transmit_science: float = 0.1

        # TODO If there is a scientist within the crew, it can reset non-rerunnable experiments
        self.has_scientist_in_crew = False

        self.run_interval = 5
        self.last_run = time.time()

    def run(self):
        if time.time() - self.last_run < self.run_interval:
            return
        self.last_run = time.time()

        names_run: Set[str] = set()
        experiments = vessel_experiments()
        for i, experiment in enumerate(experiments):
            name: str = experiment.part.name
            if experiment.inoperable or not experiment.available:
                continue
            if name in names_run:
                continue

            scientific_value = science = 0
            if experiment.science_subject is not None:
                # A value between 0 and 1
                scientific_value: float = experiment.science_subject.scientific_value
                # How much science can be gathered total?
                science_cap: float = experiment.science_subject.science_cap
                # Science that can be obtained if ran
                science: float = scientific_value * science_cap

            # Currently stored science
            current_science_value: float = 0 if not experiment.has_data or not experiment.data else experiment.data[
                0
            ].science_value

            if (
                not experiment.has_data
                and current_science_value == 0
                and (self.run_non_rerunnable_science or experiment.rerunnable)
            ):
                if science >= self.min_science and scientific_value > self.min_scientific_value:
                    logger.info(
                        f"{i}: Running experiment on part: {experiment.part.name} to obtain {science:.2f} science ({scientific_value:.2f} scientific value), experiment: {experiment.science_subject.title}"
                    )
                    experiment.run()
                    names_run.add(name)

            elif experiment.has_data and experiment.rerunnable and current_science_value < science:
                if science >= self.min_science and scientific_value > self.min_scientific_value:
                    experiment.reset()
                    # time.sleep(0.1)
                    logger.info(
                        f"{i}: Resetting experiment on part: {experiment.part.name} to obtain {science:.2f} science ({scientific_value:.2f} scientific value) and discarding old value of {current_science_value:.2f} science"
                    )
                    # experiment.run()
                    names_run.add(name)

            # for experiment in experiments:
            elif experiment.has_data and experiment.data and self.transmit_science:
                data = experiment.data[0]
                transmit_science = data.data_amount * data.transmit_value
                if transmit_science > self.min_transmit_science:
                    logger.info(
                        f"Transmitting science on part {experiment.part.name} for transmit science total of {transmit_science:.02f}"
                    )
                    experiment.transmit()


if __name__ == "__main__":
    # while vessel.situation.name in {"pre_launch"}:
    #     time.sleep(0.1)

    logger.info(f"Gathering science...")

    science = Science()
    while 1:
        time.sleep(0.1)
        science.run()

        # https://krpc.github.io/krpc/python/api/space-center/vessel.html#SpaceCenter.VesselSituation
        # if vessel.situation.name in {"landed", "splashed"}:
        #     break
    logger.info("END OF PROGRAM")
