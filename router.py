import time
import struct
import queue
import messages
import autopilot

import commands as mavs
import definitions as vars

command_queue = queue.PriorityQueue()

class Command:
    def __init__(self, priority, name, body):
        self.priority = priority
        self.name = name
        self.body = body

    def __lt__(self, other):
        return self.priority < other.priority

def put_command(command):
    command_queue.put(command)

def command_executor(stop_command):
    connection = False
    while not connection and not stop_command.is_set():
        try:
            time.sleep(2)
            mavs.connect()
            messages.display(messages.command_executor_connected, [vars.companion_computer])
            connection = True
            autopilot.state['connection'] = True
        except Exception as e:
            messages.display(messages.fatal_error, [e])
            pass

    while not stop_command.is_set():
        try:
            command = command_queue.get(timeout=1)
            execute_command(command)
            command_queue.task_done()
            time.sleep(1)
        except:
            pass

    stopped_time = time.strftime("%H:%M:%S, %Y, %d %B", time.localtime())  
    messages.display(messages.command_executor_done, [stopped_time])

def execute_command(command):
    messages.display(messages.command_executor_executing_command, 
                     [command.name, command.priority, command.body])

    if command.name in commands:
        commands[command.name](command.body)

def command_monitor(params):
    monitor = mavs.telemetry(params['target'])
    messages.display(messages.command_monitor_log, [monitor])

    rssi_bytes = monitor[3:5]
    rssi = struct.unpack('<H', rssi_bytes)[0]

    battery_voltage = float(monitor[0]) / 10
    autopilot.state['battery'] = battery_voltage
    autopilot.state['rssi'] = rssi

    if rssi > 100:
        autopilot.state['rssi_msg'] = 'Strong signal'
    else:
        autopilot.state['rssi_msg'] = 'No signal'
    
    messages.display(
            messages.command_monitor_current_rssi_and_battery, 
            [rssi, autopilot.state['rssi_msg'], battery_voltage])

def command_telemetry_viable_status(telemetry):
    altitude = struct.unpack('<i', telemetry[0:4])[0] / 100
    speed = struct.unpack('<H', telemetry[4:6])[0] / 100
    autopilot.state['speed'] = speed
    autopilot.state['altitude'] = altitude
    if speed > 1:
        messages.display(
            messages.command_telemetry_current_speed, 
            [speed])
    if altitude > 1:
        messages.display(
            messages.command_telemetry_current_altitude, 
            [altitude])

def command_telemetry_raw_imu(telemetry):
    # MSP_RAW_IMU: acc[xyz] (3x int16), gyro[xyz] (3x int16), mag[xyz] (3x int16)
    acc_x, acc_y, acc_z = struct.unpack('<hhh', telemetry[0:6])
    gyro_x, gyro_y, gyro_z = struct.unpack('<hhh', telemetry[6:12])
    mag_x, mag_y, mag_z = struct.unpack('<hhh', telemetry[12:18])

    autopilot.state['acc_x'] = acc_x
    autopilot.state['acc_y'] = acc_y
    autopilot.state['acc_z'] = acc_z
    autopilot.state['gyro_x'] = gyro_x
    autopilot.state['gyro_y'] = gyro_y
    autopilot.state['gyro_z'] = gyro_z
    autopilot.state['mag_x'] = mag_x
    autopilot.state['mag_y'] = mag_y
    autopilot.state['mag_z'] = mag_z

    messages.display(
        messages.command_telemetry_current_imu,
        [acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z, mag_x, mag_y, mag_z])

def command_telemetry_attitude(telemetry):
    # MSP_ATTITUDE: roll (int16, 0.1 deg), pitch (int16, 0.1 deg), yaw (int16, deg)
    roll_raw, pitch_raw, yaw_raw = struct.unpack('<hhh', telemetry[0:6])

    roll = roll_raw / 10.0  # Convert to degrees
    pitch = pitch_raw / 10.0  # Convert to degrees
    yaw = yaw_raw  # Already in degrees

    autopilot.state['attitude_roll'] = roll
    autopilot.state['attitude_pitch'] = pitch
    autopilot.state['attitude_yaw'] = yaw

    messages.display(
        messages.command_telemetry_current_attitude,
        [roll, pitch, yaw])

def command_telemetry_mode_change(telemetry):
    previous_throttle = autopilot.state['throttle']
    rc_chs = struct.unpack('<' + 'H' * (len(telemetry) // 2), telemetry)

    autopilot.state['roll'] = rc_chs[0]
    autopilot.state['pitch'] = rc_chs[1]
    autopilot.state['yaw'] = rc_chs[2]
    autopilot.state['throttle'] = rc_chs[3]
    autopilot.state['aux1'] = rc_chs[4]
    autopilot.state['aux2'] = rc_chs[5]
    autopilot.state['aux3'] = rc_chs[6]
    autopilot.state['aux4'] = rc_chs[7]

    aux3_raw = int(autopilot.state['aux3'])
    autopilot_mode = autopilot.state['bee_state']
    if aux3_raw == 1000:
        autopilot_mode = 'OFF'
    elif aux3_raw == 1503:
        mavs.prepare_go_forward(previous_throttle)
        time.sleep(0.1)
    elif aux3_raw == 2000:
        autopilot_mode = 'READY'

    if autopilot_mode != autopilot.state['bee_state']:
        autopilot.state['bee_state'] = autopilot_mode
        messages.display(
                    messages.bee_state_changed_to, [autopilot_mode])
        command_queue.queue.clear()

def command_telemetry(params):
    try:
        telemetry = mavs.telemetry(params['target'])
        messages.display(messages.command_telemetry_log, [telemetry])

        if telemetry != {}:
            if params['target'] == 'MSP_RAW_IMU':
                command_telemetry_raw_imu(telemetry)
            if params['target'] == 'MSP_ATTITUDE':
                command_telemetry_attitude(telemetry)
            if params['target'] == 'MSP_ALTITUDE':
                command_telemetry_viable_status(telemetry)
            if params['target'] == 'MSP_RC':
                command_telemetry_mode_change(telemetry)

        messages.display(
            messages.command_telemetry_autopilot_state,
            [autopilot.state])
    except Exception as ex:
        messages.display(
            messages.telemetry_reconnection, [ex])
        # In case of any error we will reboot connection
        mavs.reboot()


def command_init(params):
    messages.display(messages.initializing_autopilot)
    mavs.copter_init()

def command_deliver(params):
    delivered = autopilot.state['delivered']
    altitude = autopilot.state['altitude']
    speed = autopilot.state['speed']

    if delivered == False:
        # Don't go forward if drone is landed
        if altitude == 0:
            return
        
        if mavs.go_forward():
            messages.display(
                    messages.command_deliver_we_are_going_forward)
            if mavs.deliver():
                messages.display(
                    messages.command_deliver_we_are_delivering)
                autopilot.state['delivered'] = True
                messages.display(
                    messages.command_deliver_mission_completed)
                command_queue.queue.clear()

commands = {
    'INIT': command_init,
    'MONITOR': command_monitor,
    'TELEMETRY': command_telemetry,
    'DELIVER':command_deliver,
}
