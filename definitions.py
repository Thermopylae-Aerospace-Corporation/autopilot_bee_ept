# Connection Mode: 'SITL' or 'HARDWARE'
CONNECTION_MODE = 'SITL'

# SITL Configuration (TCP socket)
sitl_host = 'localhost'
sitl_port = 5761

# Hardware Configuration (serial)
hardware_serial_port = '/dev/ttyACM0'  # or COM3 for Windows
hardware_baud_rate = 115200

# Active connection settings (auto-configured based on CONNECTION_MODE)
if CONNECTION_MODE == 'SITL':
    companion_computer = f'socket://{sitl_host}:{sitl_port}'
    companion_baud_rate = None  # Not used for TCP socket
else:  # HARDWARE
    companion_computer = hardware_serial_port
    companion_baud_rate = hardware_baud_rate

logger_name = 'BEE-EPT-UA913'
logger_directory = '/home/thermopylae-aerospace/Software-Simulation/autopilot_bee_ept/logs'  # logs for the pi

default_roll = 1500
default_pitch = 1500
default_yaw = 1500
default_throttle = 1000
default_servo_aux2 = 1000
