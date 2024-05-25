import threading
import time
import serial
import logging
import json
import sys
from gpiozero import Device, Buzzer
from gpiozero.pins.rpigpio import RPiGPIOFactory
from geopy.distance import geodesic
import pynmea2
import os
import signal
import math
from random import random


def load_config():
    """ Load configuration settings from a JSON file. """
    with open('/home/pi/TreasureHunt/config.json', 'r') as f:
        return json.load(f)


CONFIG = load_config()

# Setup GPIO to use RPi.GPIO
Device.pin_factory = RPiGPIOFactory()

# Setup logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler(CONFIG['log_file_path']),
                        logging.StreamHandler()
                    ])


def convert_to_decimal(value, direction):
    """ Convert GPS value to decimal format based on the hemisphere. """
    try:
        value = float(value)
    except ValueError:
        logging.error(f"Invalid GPS value: {value}")
        return None
    factor = -1 if direction in ['S', 'W'] else 1
    return factor * abs(value)


class TreasureDetector:
    def __init__(self, treasure_location):
        self.buzzer = Buzzer(CONFIG['buzzer_pin'])
        self.ser = serial.Serial(CONFIG['serial_port'], baudrate=CONFIG['baud_rate'], timeout=1)
        self.lock = threading.Lock()
        self.running = True
        self.current_location = None
        self.current_distance = float('inf')
        self.treasure_location = treasure_location
        self.last_update_time = time.time()
        self.last_beep_time = time.time()  # Initialize last beep time
        self.is_startup_beep_done = False
        self.buzzer_state = None
        self.startup_beep()

    def fetch_gps(self):
        while self.running:
            try:
                data = self.ser.readline().decode('utf-8').strip()
                if any(data.startswith(gps_type) for gps_type in ['$GPRMC', '$GPGGA']):
                    msg = pynmea2.parse(data)
                    if hasattr(msg, 'latitude') and hasattr(msg, 'longitude'):
                        self.update_location(float(msg.latitude), msg.lat_dir, float(msg.longitude), msg.lon_dir)
            except (serial.SerialException, pynmea2.ParseError) as e:
                logging.error(f"Communication or parsing error: {e}")
            finally:
                self.ser.reset_input_buffer()

    def update_location(self, lat, lat_dir, lon, lon_dir):
        if not all([lat, lat_dir, lon, lon_dir]):  # Basic check for data completeness
            logging.warning("Incomplete GPS data received.")
            return
        new_location = (convert_to_decimal(lat, lat_dir), convert_to_decimal(lon, lon_dir))
        with self.lock:
            if new_location != self.current_location:
                self.current_location = new_location
                self.current_distance = geodesic(self.current_location, self.treasure_location).meters
                self.last_update_time = time.time()
                logging.info(f"Updated GPS location: {self.current_location} - Distance: {self.current_distance:.2f} m")

    def startup_beep(self):
        try:
            self.buzzer.beep(on_time=0.2, off_time=1, n=2, background=False)
            self.is_startup_beep_done = True
            logging.info("Startup beep sequence completed.")
        except Exception as e:
            logging.error(f"Failed to complete startup beep sequence: {e}")

    def beep_continuously(self):
        while self.running:
            self.fetch_gps()
            off_time = self.get_off_time(self.current_distance)
            self.buzzer.beep(on_time=0.2, off_time=off_time, n=1, background=False)


    def get_off_time(self, distance):
        if distance > 50:
            on_time = 0.1  # Constant on-time
            off_time = random()  # Constant on-time

        # self.ensure_buzzer_off()  # Too far, no beeping
        else:
            on_time = 0.1  # Constant on-time
            # Adjust off-time based on distance
            if distance <= 5:
                off_time = 0.1  # Very close to the target, frequent beeping
            else:
                min_off_time = 0.2  # Increased minimum off-time for greater distances
                max_off_time = 5.0  # Increased maximum off-time
                max_distance = 50
                # Linearly scale the off-time based on the distance
                off_time = max_off_time - ((max_distance - distance) / max_distance) * (max_off_time - min_off_time)

            current_time = time.time()
            if current_time - self.last_beep_time > off_time:
                self.set_buzzer(on_time, off_time)
                self.last_beep_time = current_time

        return off_time


    def set_buzzer(self, on_time, off_time):
        if self.buzzer_state != (on_time, off_time):
            self.buzzer.beep(on_time=on_time, off_time=off_time)
            self.buzzer_state = (on_time, off_time)
            logging.info(
                f"Buzzer adjusted: on_time={on_time}s, off_time={off_time}s at distance {self.current_distance}m")

    def ensure_buzzer_off(self):
        if self.buzzer.is_active:
            self.buzzer.off()
            self.buzzer_state = None
            logging.info("Buzzer turned off due to inactivity or distance.")

    def run(self):
        try:
            self.beep_continuously()
        finally:
            self.stop()  # Ensure resources are always cleaned up

    def stop(self):
        self.running = False
        self.buzzer.off()


def handle_signal(signum, frame):
    global detector
    logging.info("Signal received: stopping...")
    detector.stop()


if __name__ == "__main__":
    # Command line arguments to override treasure coordinates
    if len(sys.argv) > 2:
        treasure_coords = (float(sys.argv[1]), float(sys.argv[2]))
    else:
        treasure_coords = CONFIG['treasure_coords']

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    detector = TreasureDetector(treasure_coords)
    detector.run()
