#!/usr/bin/python3

# Pyserial
import serial

# python-daemon
import daemon

import sys
import os
import re
import subprocess
import signal
import time

# Allows running multiple scripts/commands with a single mode
# Eg.: [['echo', 'a'], ['echo', 'b']] -> echo "a" && echo "b"
# Passing in a single command array as 'commands' also work
def runMacro(actions, new_session=True):
    if isinstance(actions, ToggleableAction):
        actions.toggle()
        return

    if isinstance(actions, str) or isinstance(actions[0], str):
        return subprocess.Popen(actions, shell=False, start_new_session=new_session)

    for command in actions:
        subprocess.Popen(command, shell=False, start_new_session=new_session)

# Only accepts single string command (in order to create only one Popen object)
class ToggleableAction:
    def __init__(self, command: str, initial_state = None, fallback_kill_command = None):
        self.command = command

        if initial_state is None:
            self.state = False
        else:
            self.state = runMacro(initial_state, False).returncode == 0
        self.init_state = self.state

        self.kill = fallback_kill_command
        self.proc = None

    def toggle(self):
        if self.state is False:
            self.proc = runMacro(self.command)
            self.state = True
        else:
            if self.proc is None and self.kill is not None:
                runMacro(self.kill)
            else:
                self.proc.terminate()
            
            self.state = False


# Path to PID of running daemon
pid_path = '/var/run/user/1001/unokb.pid'

# Serial port communication channel
serial_port = '/dev/ttyACM0'
com_channel = serial.Serial()

# Keeps the daemon alive even if a (known) exception occured (a SerialException)
#
# Set this to True if you want the daemon to be running indefinitely
# on your machine, regardless of whether the Arduino board is connected
# to the machine or not. False will make it exit once the board is disconnected.
#
# Even when True, the daemon will still be killed if a generic exception is thrown,
# like when a macro fails to run.
keep_alive = False

# Available macros.
# Supports three types of macros:
# 1. Simple command: Use str as command or path to script
#    Eg.: 'NameOfMacro' : 'command',
#         'NameOfMacro' : '/path/to/script',
# 2. Composite command: Use str with the whole command or a list with the arguments
#    Eg.: 'NameOfMacro' : 'command arg1 arg2 arg3',
#         'NameOfMacro' : ['command', 'arg1', 'arg2', 'arg3']
# 3. Multiple commands: Use list of lists of commands with arguments
#    Eg.: 'NameOfMacro' : [['command1', 'arg1', 'arg2', 'arg3'], ['command2', 'arg4']]
macros = {
    'Mute':     '/home/low/Documents/scripts/discord-mute.sh',
    'Deafen':   '/home/low/Documents/scripts/discord-deafen.sh',
    'VolUp':    ['pactl', 'set-sink-volume', '@DEFAULT_SINK@', '+10%'],
    'VolDown':  ['pactl', 'set-sink-volume', '@DEFAULT_SINK@', '-10%'],
    'StartMic': '/home/low/Documents/scripts/mic_start_script.sh',
    'StopMic':  '/home/low/Documents/scripts/mic_kill.sh',
    'Mic':      ToggleableAction('/home/low/Documents/scripts/mic_start_script.sh',
                                 '/home/low/Documents/scripts/mic_check.sh',
                                 '/home/low/Documents/scripts/mic_kill.sh'),
    'Reverb':   ToggleableAction('/home/low/Documents/scripts/mic/reverb.sh')
}

# Available modes for usage
#         button 1  button 2   button 3    button 4
modes = [['Mic'  , 'Reverb' , 'VolUp'   , 'VolDown'],
         ['Mute'  , 'Deafen' , 'StartMic', 'StopMic'],
         ['VolUp' , 'VolDown', 'StartMic', 'StopMic']]

# Parses the command received on the serial port
# to its original equivalent
binary_command = re.compile(r"b'(.*)'", re.IGNORECASE)

# Parses the original command into its parts ({command}={pin number})
parse_command = re.compile(r"(.*)=([0-9+-]*)", re.IGNORECASE)

# Parses a command received via the serial port
def receiveCommand(com_channel : serial.Serial):
    # Receive a command (which all end in \n)
    command = str(com_channel.readline().strip())
    true_command = binary_command.match(command)

    if true_command is not None:
        true_command = true_command.group(1)
        parsed_command = parse_command.match(true_command)
        if parsed_command is None:
            return (None, None)
        return (parsed_command.group(1), parsed_command.group(2))
    else:
        return (None, None)

# Sends the current mode names to the Arduino via the serial port
def setMode(com_channel : serial.Serial, current_mode : int):
    com_channel.write(bytes('mode_setup\0\n', 'ascii'))
    
    for s in modes[current_mode]:
        for x in s:
            com_channel.write(bytes(x, 'ascii'))

        com_channel.write(bytes('\0\n', 'ascii'))

def openSerialPort(com_channel : serial.Serial):
    while not com_channel.is_open:
        time.sleep(1)
        if not os.path.exists(serial_port):
            continue
        try:
            com_channel.open()
        except serial.serialutil.SerialException:
            pass

def main():
    # Currently selected mode
    current_mode = 0

    com_channel.port = serial_port
    com_channel.setDTR(False)
    openSerialPort(com_channel)
        
    while True:
        try:
            command, arg = receiveCommand(com_channel) 
            if command is None:
                continue

            if command == 'btn_pressed':
                pressed_button = int(arg)
                runMacro(macros[modes[current_mode][pressed_button - 1]])

            elif command == 'mode_changed':
                change = int(arg)
                current_mode = (current_mode + change) % len(modes)
                setMode(com_channel, current_mode)

        except serial.serialutil.SerialException:
            if not keep_alive:
                os.kill(os.getpid(), signal.SIGTERM)
            else:
                com_channel.close()
                openSerialPort(com_channel)
        except Exception as e:
            print("An error has occured. The daemon will be killed.", file=sys.stderr)
            print(e, file=sys.stderr)
            os.kill(os.getpid(), signal.SIGTERM)

def shutdown(signum, frame):
    for action in macros.items():
        true_act = action[1]
        if isinstance(true_act, ToggleableAction):
            if true_act.state != true_act.init_state:
                true_act.toggle()
    try:
        if com_channel.is_open:
            com_channel.write(bytes('host_disconnect\0\n', 'ascii'))
            com_channel.close()
    except serial.serialutil.SerialException:
        print("Exiting daemon unable to write to serial port. It's NOT a bug if you disconnected your board.")

    os.remove(pid_path)
    sys.exit(0)



try:
    with open(pid_path, 'x') as f:
        print(f'PID file created at {pid_path}')
except FileExistsError:
    with open(pid_path, 'r') as f:
        pid = int(f.readline())
        try:
            os.kill(pid, signal.SIGTERM)
            print('Running daemon terminated. Have a good day!')
            sys.exit(0)
        except ProcessLookupError:
            print('No process with PID in the PID file.', file=sys.stderr)
            print('The last daemon must have exited abnormally.', file=sys.stderr)
            print('Invalid PID will be overwritten with a new instance.', file=sys.stderr)

with daemon.DaemonContext(
    files_preserve=[],
    stdout=sys.stdout,
    stderr=sys.stderr,
    signal_map={
        signal.SIGTERM: shutdown
    }):

    try:
        with open(pid_path, 'w') as f:
            f.write(str(os.getpid()))
    except:
        sys.exit(1)

    main()
