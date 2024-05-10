import threading
import logging
import pynmea2
import mgrs
import math
import RPi.GPIO as GPIO
import time
import serial

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def convert_to_decimal(value, direction):
    try:
        value = float(value)
    except ValueError:
        logging.error(f"Invalid GPS value: {value}")
        return None
    factor = -1 if direction in ['S', 'W'] else 1
    return factor * abs(value)

def calculate_distance(x1, y1, x2, y2):
    return round(math.sqrt((int(x2) - int(x1))**2 + (int(y2) - int(y1))**2))

class Buzzer:
    def __init__(self, pin):
        self.pin = pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.pin, GPIO.OUT)

    def beep(self, on_time, off_time, n=1):
        """Make the buzzer beep with specified on-time, off-time, and repetitions."""
        for _ in range(n):
            GPIO.output(self.pin, GPIO.HIGH)
            time.sleep(on_time)
            GPIO.output(self.pin, GPIO.LOW)
            time.sleep(off_time)

    def adjust_buzzer_frequency(self, distance):
        if distance > 30:
            self.beep(0.1, 5)
        elif 20 < distance <= 30:
            self.beep(0.1, 2)
        elif 10 < distance <= 20:
            self.beep(0.1, 1)
        elif 5 < distance <= 10:
            self.beep(0.1, 0.5)
        elif distance <= 5:
            self.beep(0.1, 0.1)

    def cleanup(self):
        GPIO.cleanup()

class GPSReader:
    def __init__(self, port='/dev/serial0', baudrate=9600, buzzer_pin=23):
        self.ser = serial.Serial(port, baudrate=baudrate, timeout=1)
        self.running = True
        self.mgrs_converter = mgrs.MGRS()
        self.buzzer = Buzzer(buzzer_pin)
        self.is_startup_beep_done = False

    def startup_beep(self):
        """Perform a startup beep sequence."""
        try:
            self.buzzer.beep(on_time=0.2, off_time=1, n=2)  # Beep twice
            self.is_startup_beep_done = True
            logging.info("Startup beep sequence completed.")
        except Exception as e:
            logging.error(f"Failed to complete startup beep sequence: {e}")

    def fetch_and_output_gps(self):
        if not self.is_startup_beep_done:
            self.startup_beep()
        target_x, target_y = "58929", "90966"
    
        while self.running:
            try:
                data = self.ser.readline().decode('utf-8').strip()
                if data.startswith('$GPGGA'):
                    msg = pynmea2.parse(data)
                    if hasattr(msg, 'latitude') and hasattr(msg, 'longitude'):
                        lat = convert_to_decimal(msg.latitude, msg.lat_dir)
                        lon = convert_to_decimal(msg.longitude, msg.lon_dir)
                        if lat is not None and lon is not None:
                            mgrs_coords = self.mgrs_converter.toMGRS(lat, lon)
                            x = mgrs_coords[5:10]
                            y = mgrs_coords[10:15]
                            distance = calculate_distance(x, y, target_x, target_y)
                            self.buzzer.adjust_buzzer_frequency(distance)
                            logging.info(f"Coordinates: {x} {y}, Distance to Target: {distance}m")
            except (serial.SerialException, pynmea2.ParseError, ValueError) as e:
                logging.error(f"Communication, parsing, or conversion error: {e}")
            finally:
                self.ser.reset_input_buffer()

    def run(self):
        gps_thread = threading.Thread(target=self.fetch_and_output_gps)
        gps_thread.start()
        gps_thread.join()

    def stop(self):
        self.running = False
        self.ser.close()
        self.buzzer.cleanup()
        logging.info("GPS Reader stopped and serial port closed.")

if __name__ == "__main__":
    gps_reader = GPSReader()
    try:
        gps_reader.run()
    except KeyboardInterrupt:
        gps_reader.stop()
