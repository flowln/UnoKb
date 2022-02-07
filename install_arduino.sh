#!/bin/bash

arduino-cli compile --fqbn arduino:avr:uno $(pwd)
arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:avr:uno $(pwd) --verbose
