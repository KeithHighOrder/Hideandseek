
import serial
import time

def connect_to_dwm1001(port='/dev/ttyACM0', baud_rate=115200):
    """ Establish a connection to the DWM1001 module """
    try:
        ser = serial.Serial(port, baud_rate, timeout=1)
        print("Connected to DWM1001-DEV on", port)
        return ser
    except serial.SerialException as e:
        print(f"Failed to connect on {port}: {str(e)}")
        return None

def send_command(ser, command):
    """ Send a command to the DWM1001 module """
    if ser:
        ser.write((command + '\r').encode())
        time.sleep(1)  # Wait for the command to take effect

def parse_location_data(data):
    """ Parse location data from the incoming data stream """
    if "POS" in data:
        try:
            parts = data.split(',')
            pos_index = parts.index("POS") + 1  # Find the index of 'POS'
            x, y, _ = parts[pos_index:pos_index+3]  # Extract X, Y coordinates
            print(f"Position - X: {x.strip()}, Y: {y.strip()}")
        except (IndexError, ValueError) as e:
            print(f"Error parsing position data: {str(e)}")

def read_continuous_data(ser):
    """ Continuously read and process data from the DWM1001 module """
    try:
        print("Reading location data. Press Ctrl+C to stop.")
        buffer = ""
        while True:
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting).decode('utf-8', errors='replace')
                buffer += data
                while '\r\n' in buffer:
                    line, buffer = buffer.split('\r\n', 1)
                    parse_location_data(line)
    except KeyboardInterrupt:
        print("\nStopped reading data.")
    except Exception as e:
        print(f"Error while reading data: {str(e)}")

def main():
    ser = connect_to_dwm1001()
    if ser:
        send_command(ser, "lec")  # Start continuous location data streaming
        read_continuous_data(ser)
        ser.close()  # Ensure the connection is closed properly

if __name__ == "__main__":
    main()

