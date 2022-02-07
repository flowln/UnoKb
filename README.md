# UnoKb - Ayy another macro keyboard 
This is a simple macro keyboard made to work with an Arduino Uno board without firmware modification. The board communicates with a Python program on the computer side via the serial port. Currently it only works on Linux!

## Dependencies
For the arduino side, if you want LCD support (enabled by default), you'll need [LiquidDisplay](https://www.arduino.cc/en/Reference/LiquidCrystal). You can install it via the Library Manager in Arduino IDE, or via arduino-cli with `arduino-cli update && arduino-cli lib install LiquidCrystal`.
On the Python side, you'll need Python 3.x with the following external modules:
- [pyserial](https://pypi.org/project/pyserial/)
- [python-daemon](https://pypi.org/project/python-daemon/) 

## Files
There are four files on this repository:
1. [unokb.py](unokb.py): This is the python script that spawns and kills the daemon on the computer. It receives the inputs from the board and translates that into commands and/or scripts to be run on the PC. It also sends to the board the selected mode.
2. [UnoKb.ino](UnoKb.ino): This is the arduino program. It has options to disable LCD support before compilation, as well as customize the pin layout and the latency settings. It polls the input pins every _x_ milliseconds (by default, _x_ is ~50ms), and sends the appropriate message to the serial port in case any pin is pressed.
3. [install\_arduino.sh](install_script.sh): This is a simple linux utility script to compile and install the `UnoKb.ino` program on the board.
4. [monitor.sh](monitor.sh): Another simple linux utility, to monitor the serial port for debug. I kept forgetting the command to do so, so that's why this script exists. :P

## How to use
Firstly, you should take a look at both the .ino and .py files, and adjust them to your preferences. Probably the most important things to take note are the pin numbers in the .ino file, and the macros / modes in the .py file.
Once this is done, install the sketch with your preferred tool (if on Linux, the `install_arduino.sh` script should work if you have arduino-cli installed on your machine). 
Finally, you (should) be able to start the Python program, which will spawn a daemon process that communicates with the board on the background. To stop the daemon, just run the python program again.

## Debugging
To debug problems on the board, make sure the python program is not running, and use the monitor (either via arduino-cli or via the Arduino IDE interface) to see what's going on in the serial port. There's also a debug setting in the .ino file, which prints some more debug info to the port. 
For the Python side, make sure the `stdout` and `stderr` lines at the end of the file are uncommented, as they can provide valuable information about what's going wrong.

## TODO:
- Add Windows support
