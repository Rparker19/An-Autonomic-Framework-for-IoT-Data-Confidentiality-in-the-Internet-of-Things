import argparse
from datetime import datetime
import glob
import joblib
from kasa_energy import EnergyMonitor
import logging
import oqs
import os
from pathlib import Path
import random
import time



class AutonomicManager:

    def __init__(self, device_id, algorithm, current, voltage, capacity=2000, security_level=1, interval=5, classifier_filename='dtc.joblib', is_online=False, device_ip=""):
        self.device_id = device_id
        self.algorithm = algorithm
        self.current = current
        self.voltage = voltage
        self.battery_capacity = capacity
        self.security_level = security_level
        self.interval = interval
        self.classifier = classifier_filename
        self.loop_time = datetime.now()
        self.energy_monitor = False
        if is_online:
            self.energy_monitor = EnergyMonitor(device_ip=device_ip)
            self.energy_monitor.start_background_thread()
        logging.info("Autonomic manager initialized.")

    def get_power(self):
        time_since_last_loop = datetime.now()
        time_difference = time_since_last_loop - self.loop_time

        if self.energy_monitor:
            # Calculate energy consumed since last loop using kasa data
            start_index = 0
            for time in self.energy_monitor.timestamps:
                if time > self.loop_time:
                    start_index = self.energy_monitor.timestamps.index(time)
                    break;
            charge_decrease = sum(self.energy_monitor.power_data[start_index:])
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
        self.security_level_friend = random.randint(1, 5)
        logging.info(f"{self.device_id} ANALYZE: Security level of friend is: {self.security_level_friend}")

    def plan(self):
        """Load classifier and use to choose the algorithm for signing.
        """
        model = joblib.load(self.classifier)
        (self.algorithm, self.current, self.voltage) = model.predict([self.power_level, self.security_level, self.security_level_friend]) # add other vars once I have a model
        logging.info(f"{self.device_id} PLAN: Use {self.algorithm}")

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
                    bytes = file.read()

                    # Signer signs the message
                    signature = signer.sign(bytes)

                    # Verifier verifies the signature
                    is_valid = verifier.verify(bytes, signature, signer_public_key)
                    print(f"Valid signature ({Path(filename).name})? {is_valid}\t|\t")

    def execute(self):
        """Execute signing using chosen algorithm
        """
        num_files = random.randint(1, 10)
        logging.info(f"{self.device_id} EXECUTE: Signing {num_files} files")
        files = self.create_random_files(num_files)
        self.signing(self.algorithm, files)

    def loop(self):
        logging.info("Starting autonomic loop for {self.device_id}")
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
    args = parser.parse_args()

    am = AutonomicManager(args.device_id, algorithm="ML-DSA-44", current=0.037, voltage=117.5)
    am.loop()
