import argparse
from datetime import datetime
import glob
import joblib
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from kasa_energy import EnergyMonitor
import logging
import oqs
import os
import random
import time
import pandas as pd


def setup_logging(log_file="autonomic-manager.log"):
    log_path = Path(__file__).parent / log_file
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(log_path, mode="a"),
            logging.StreamHandler(),
        ],
    )
    return log_path


class AutonomicManager:

    def __init__(self, device_id, algorithm, current, voltage, capacity=2000, security_level=1, interval=5, classifier_filename='dtc.joblib', is_online=False, device_ip="192.168.11.105"):
        self.device_id = device_id
        self.algorithm = algorithm
        self.current = current
        self.voltage = voltage
        self.battery_capacity = capacity
        self.security_level = security_level
        self.interval = interval
        self.classifier = self._resolve_classifier_path(classifier_filename)
        self.loop_time = datetime.now()
        self.energy_monitor = None
        self.has_charge = True      # Assuming device starts with charge, will be set to False when battery capacity is depleted.
        if is_online:
            self.energy_monitor = EnergyMonitor(device_ip=device_ip)
            self.energy_monitor.start_background_thread()
        logging.info(f"Classifier path: {self.classifier}")
        logging.info("Autonomic manager initialized.")

    @staticmethod
    def _resolve_classifier_path(classifier_filename):
        classifier_path = Path(classifier_filename)
        if classifier_path.is_absolute():
            return str(classifier_path)

        script_dir = Path(__file__).resolve().parent
        candidates = [
            script_dir / classifier_path,
            script_dir.parent / classifier_path,
        ]

        if classifier_path.parent == Path("."):
            candidates.append(script_dir.parent / "models" / classifier_path.name)

        for candidate in candidates:
            if candidate.exists():
                return str(candidate)

        return str(candidates[0])

    def get_power(self):
        time_since_last_loop = datetime.now()
        time_difference = time_since_last_loop - self.loop_time

        if self.energy_monitor:
            self.energy_monitor.get_latest_data()

            # Calculate energy consumed since last loop using kasa data
            start_index = 0
            for idx, ts in enumerate(self.energy_monitor.timestamps):
                try:
                    ts_dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S.%f")
                except ValueError:
                    continue

                if ts_dt > self.loop_time:
                    start_index = idx
                    break

            charge_decrease = 0.0
            for socket_powers in self.energy_monitor.power_data.values():
                if start_index < len(socket_powers):
                    charge_decrease += sum(socket_powers[start_index:])
        else: 
            # Calculate energy consumed using voltage and current data for current algorithm
            # Assume relationship is linear for experimental simplicity
            charge_decrease = self.voltage * self.current * (time_difference.total_seconds() / 3600)
            
        self.battery_capacity -= charge_decrease
        self.loop_time = time_since_last_loop
        

    def monitor(self):
        """Monitor remaining battery capacity.
        If capacity is at or below zero, set has_charge flag to False
        """
        self.get_power()
        if self.battery_capacity <= 0:
            self.has_charge = False
        logging.info(f"{self.device_id} MONITOR: Current algorithm: {self.algorithm}")
        logging.info(f"{self.device_id} MONITOR: Current power level: {self.battery_capacity}")

    def analyze(self):
        """Determine security level of hypothetical signed data recipient
        """
        logging.info(f"{self.device_id} ANALYZE: Security level is: {self.security_level}")
        # self.security_level_friend = random.randint(1, 5)
        # logging.info(f"{self.device_id} ANALYZE: Security level of friend is: {self.security_level_friend}")

    def plan(self):
        """Load classifier and use to choose the algorithm for signing.
        """
        model = joblib.load(self.classifier)
        #(self.algorithm, self.current, self.voltage) = model.predict([self.power_level, self.security_level, self.security_level_friend]) # add other vars once I have a model

        feature_names = getattr(model, "feature_names_in_", None)
        if feature_names is None:
            raise ValueError("Classifier is missing feature_names_in_; retrain and export with feature names.")

        # Build one input row with the exact columns used during training.
        feature_values = {name: 0.0 for name in feature_names}
        feature_values["Current"] = float(self.current)
        feature_values["Voltage"] = float(self.voltage)
        feature_values["Power"] = float(self.current * self.voltage)
        feature_values["Execution Time"] = float(self.interval) # TODO: self.interval is not execution time, need to calculate actual execution time of signing and use that here instead for more accurate predictions. For now, just using interval as a placeholder.
        feature_values["Time Per File"] = float(self.interval)  # TODO: same as above, need to calculate actual time per file for more accurate predictions.

        input_frame = pd.DataFrame([feature_values], columns=list(feature_names))
        self.algorithm = model.predict(input_frame)[0]
        logging.info(f"{self.device_id} PLAN: Use {self.algorithm}; predicted with features: {[k for k, v in feature_values.items() if v != 0.0]} out of {len(feature_values)} features.")

    def create_random_files(self, num_files, size_in_mb=100, filename="testfile", extension="bin"):
        for i in range(num_files):
            with open(f"{Path(__file__).parent / f'{Path(filename).stem}_{i}.{extension}'}", "wb") as f:
                f.write(os.urandom(size_in_mb * 1024 * 1024))

        return glob.glob(f"{Path(__file__).parent}/*.{extension}")

    def signing(self, alg, files):
        # Create signer and verifier
        with oqs.Signature(alg) as signer, oqs.Signature(alg) as verifier:
            # Signer generates its keypair
            signer_public_key = signer.generate_keypair()

            # Sign each file in the list
            for filename in files:
                with open(filename, 'rb') as file:
                    file_bytes = file.read()

                    # Signer signs the message
                    signature = signer.sign(file_bytes)

                    # Verifier verifies the signature
                    is_valid = verifier.verify(file_bytes, signature, signer_public_key)
                    print(f"Valid signature ({Path(filename).name})? {is_valid}\t|\t")

    def execute(self):
        """Execute signing using chosen algorithm
        """
        num_files = random.randint(1, 10)
        logging.info(f"{self.device_id} EXECUTE: Signing {num_files} files")
        files = self.create_random_files(num_files)
        # Start measuring CPU, memeory, and execution times here and use those as features for future predictions once I have a model trained with those features. For now, just using interval as a placeholder for execution time in the classifier input.    
        self.signing(self.algorithm, files)

    def loop(self):
        logging.info(f"Starting autonomic loop for {self.device_id}")
        while self.has_charge:
            try:
                self.monitor()
                if not self.has_charge:
                    break;
                self.analyze()
                self.plan()
                self.execute()
                time.sleep(self.interval)
            except Exception as ex:
                logging.error(f"An error occurred in the autonomic loop: {ex}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("device_id")
    parser.add_argument("--algorithm", type=str, default="ML-DSA-44")
    parser.add_argument("--current", type=float, default=0.037)
    parser.add_argument("--voltage", type=float, default=117.5)
    parser.add_argument("--capacity", type=int, default=2000)
    parser.add_argument("--security_level", type=int, default=1)
    parser.add_argument("--interval", type=int, default=5)
    parser.add_argument("--classifier", type=str, default="models/dtc.joblib")
    parser.add_argument("--is_online", action='store_true', default=True)
    parser.add_argument("--log_file", type=str, default="autonomic-manager.log")
    args = parser.parse_args()

    log_path = setup_logging(args.log_file)
    logging.info(f"Logging to {log_path}")

    am = AutonomicManager(args.device_id, 
                          algorithm=args.algorithm, 
                          current=args.current, 
                          voltage=args.voltage, 
                          capacity=args.capacity, 
                          security_level=args.security_level, 
                          interval=args.interval, 
                          classifier_filename=args.classifier, 
                          is_online=args.is_online)
    am.loop()