import joblib
import logging
import random
import time

class AutonomicManager:

    def __init__(self, algorithm, current, voltage, capacity=2000, security_level=1, interval=5, classifier_filename='dtc.joblib'):
        self.algorithm = algorithm
        self.current = current
        self.voltage = voltage
        self.battery_capacity = capacity
        self.security_level = security_level
        self.interval = interval
        self.classifier = classifier_filename
        self.loop_time = time.time()
        logging.info("Autonomic manager initialized.")

    def get_power(self):
        time_since_last_loop = time.time()
        # Assume relationship is linear for experimental simplicity
        charge_decrease = self.voltage * self.current * ((time_since_last_loop - self.loop_time)/ 360)
        self.battery_capacity -= charge_decrease
        self.loop_time = time_since_last_loop

    def monitor(self):
        # Receive message from server
        self.get_power()
        if self.battery_capacity <= 0:
            self.has_charge = False
        logging.info(f"MONITOR: Current algorithm: {self.algorithm}")
        logging.info(f"Current power level: {self.battery_capacity}")

    def analyze(self):
        logging.info(f"ANALYZE: Security level is: {self.security_level}")
        self.security_level_friend = random.randint(1, 5) # this is the part that could be replaced with analyzing a message from another AM
        logging.info(f"ANALYZE: Security level of friend is: {self.security_level_friend}")

    def plan(self):
        # Reference decision tree here to choose algorithm
        model = joblib.load(self.classifier)
        (self.algorithm, self.current, self.voltage) = model.predict([self.power_level, self.security_level, self.security_level_friend]) # add other vars once I have a model
        logging.info(f"PLAN: Use {self.algorithm}")

    def execute(self):
        # Send new message
        logging.info(f"EXECUTE: Sending signed message")

    def loop(self):
        logging.info("Starting autonomic loop")
        while self.has_charge:
            try:
                self.monitor()
                self.analyze()
                self.plan()
                self.execute()
                time.sleep(self.interval)
            except Exception as ex:
                logging.error(f"An error occurred in the autonomic loop: {ex}")

if __name__ == "__main__":
    am = AutonomicManager(algorithm="ML-DSA-44", current=0.037, voltage=117.5)
    am.loop()
