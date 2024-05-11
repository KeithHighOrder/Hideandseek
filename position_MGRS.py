import serial
import threading
import logging
import pynmea2
import mgrs

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def convert_to_decimal(value, direction):
    """ Convert GPS value to decimal format based on the hemisphere. """
    try:
        value = float(value)
    except ValueError:
        logging.error(f"Invalid GPS value: {value}")
        return None
    factor = -1 if direction in ['S', 'W'] else 1
    return factor * abs(value)

class GPSReader:
    def __init__(self):
        # Manually set serial port and baud rate
        self.ser = serial.Serial('/dev/serial0', baudrate=9600, timeout=1)
        self.running = True
        self.mgrs_converter = mgrs.MGRS()

    def fetch_and_output_gps(self):
        """ Continuously fetch GPS data, parse it, and output formatted MGRS coordinates and signal quality. """
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
                            # Extract and format x and y
                            x = mgrs_coords[5:10]
                            y = mgrs_coords[10:15]
                            formatted_coords = f"{x} {y}"
                            signal_quality = msg.gps_qual
                            logging.info(f"Coordinates: {formatted_coords}, Signal Quality: {signal_quality}")
            except (serial.SerialException, pynmea2.ParseError, ValueError) as e:
                logging.error(f"Communication, parsing, or conversion error: {e}")
            finally:
                self.ser.reset_input_buffer()

    def run(self):
        try:
            gps_thread = threading.Thread(target=self.fetch_and_output_gps)
            gps_thread.start()
            gps_thread.join()
        except KeyboardInterrupt:
            logging.info("GPS Reader interrupted and stopping...")
            self.stop()

    def stop(self):
        self.running = False
        self.ser.close()
        logging.info("GPS Reader stopped and serial port closed.")

if __name__ == "__main__":
    gps_reader = GPSReader()
    gps_reader.run()
