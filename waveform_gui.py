'''
Waveform experiment GUI

Oxford Neural Interfacing
Written by Conor Keogh
conor.keogh@nds.ox.ac.uk
19/03/2024

Graphical interface for data collection from waveform system
Uses custom hardware and drivers
Saves data to file

Need to:
    - Specify waveform: tonic or wavelet
    - Specify frequency
    - Specify amplitude
    - Send
    - Specify duration
    - Stimulate

'''

## Imports
import numpy as np
import time
from threading import Thread

import os.path

from dearpygui.core import *
from dearpygui.simple import *

# Import WaveWriter library
import wavewriter

''' Declare WaveWriter object '''
device = wavewriter.WaveWriter()

''' Define state transition callbacks '''
''' Sets behaviour for transitioning between interface states
    Can only move through set states:
        Entry -> Connect
        Connect -> StartSession
        StartSession -> Next
        Next -> EndSession
        End resets state to Entry
    Buttons + status set according to state
    Flags set to define data thread behaviour '''

# Connect to device
def connect_callback(sender, data):
    '''
    Runs when connect button clicked
    Connects to device
    Enables start button
    '''
    # Connect to device
    device.connect()

    # Reconfigure start -> end session
    configure_item("Connect", enabled=False)
    configure_item("Start session", enabled=True,
                   callback=startSession_callback)
    configure_item("End session", enabled=False)

    # Update status
    set_value("##DeviceStatus", "Connected")
    configure_item("##DeviceStatus", color=[0,255,0])
    set_value("##OverallStatus", "Device connected")

# Start session
def startSession_callback(sender, data):
    '''
    Run when start session clicked
    Parses inputs
    Disables all inputs
    Converts start to stop button
    Updates session status
    Updates overall status

    Loads waveforms
    '''
    # Parse inputs
    '''
    Need to:
        Get inputs
        Check validity
        Set flag based on this
        If OK: continue
        If not: stop and put error in status
        Also: check files, etc.
    '''

    # Reconfigure start -> end session
    configure_item("End session", enabled=True, callback=endSession_callback)
    configure_item("Start session", enabled=False)

    # Update status
    set_value("##SessionStatus", "Started")
    configure_item("##SessionStatus", color=[0,255,0])
    set_value("##OverallStatus", "Session started")

    # Enable running experiment
    configure_item("Waveform##input", enabled=True)
    configure_item("Frequency (Hz)##input", enabled=True)
    configure_item("Amplitude (mA)##input", enabled=True)
    configure_item("Duration (s)##input", enabled=False)
    configure_item("Send", enabled=True, callback=send_waveform_callback)
    configure_item("Stimulate", enabled=False)

# End session
def endSession_callback(sender, data):
    '''
    Runs when session ended
    Can be ended at any time after started
    Resets all flags
    Disables all control methods
    Re-enables inputs
    Updates all statuses
    Allows new session to be started
    '''
    # Disconnect from system

    # Re-configure stop -> start session
    configure_item("Connect", enabled=True, callback=connect_callback)
    configure_item("Start session", enabled=False)
    configure_item("End session", enabled=False)

    configure_item("Waveform##input", enabled=False)
    configure_item("Frequency (Hz)##input", enabled=False)
    configure_item("Amplitude (mA)##input", enabled=False)
    configure_item("Duration (s)##input", enabled=False)
    configure_item("Send", enabled=False)
    configure_item("Stimulate", enabled=False)

    # Update status
    set_value("##SessionStatus", "Not started")
    configure_item("##SessionStatus", color=[255,0,0])
    set_value("##DeviceStatus", "Not connected")
    configure_item("##DeviceStatus", color=[255,0,0])
    set_value("##OverallStatus", "Ready to connect")

# Stimulate callback
def send_waveform_callback(sender, data):
    '''
    Get data from amplitude and duration fields
    Run stimulation
    '''
    # Get intended waveform
    waveform_id = get_value("Waveform##input")
    waveforms = ["Tonic", "Sinusoidal", "Wavelet", "Offset wavelet"]
    waveform = waveforms[waveform_id]
    print(waveform)

    # Get frequency
    frequency = get_value("Frequency (Hz)##input")

    # Get amplitude
    amplitude = get_value("Amplitude (mA)##input")

    # Send waveform
    print(f"{waveform}: {frequency}Hz, {amplitude}mA")
    
    if waveform == 'Tonic':
        v, t = wavewriter.generate_tonic(
            amplitude, # mA
            frequency, # Hz
            30, # us
            biphasic = True
        )
        
    elif waveform == 'Sinusoidal':
        v, t = wavewriter.generate_sine(
            amplitude, # mA
            frequency, # Hz
            1 # Cycles
        )
        
    elif waveform == 'Wavelet':
        v, t = wavewriter.generate_wavelet(
            amplitude, # mA
            frequency, # Hz
            40, # Hz modulating
            4000 # Standard deviation
        )
        
    elif waveform == 'Offset wavelet':
        v, t = wavewriter.generate_wavelet_modulated(
            amplitude, # mA
            frequency, # Hz
            40, # Hz modulating
            4000, # Standard deviation
        )

    
    # Deactivate stimulate button (if active)
    configure_item("Stimulate", enabled=False)
    configure_item("Send", enabled=False)
    configure_item("End session", enabled=False)
    
    # Send waveform
    v, t = wavewriter.convert_waveform(v, t)
    device.send_waveform(v)

    # Update current waveform display
    set_value("##CurrentWaveform", f"{waveform}")
    set_value("##CurrentFrequency", f"{frequency}")
    set_value("##CurrentAmplitude", f"{amplitude}")
    
    # Activate stimulate button
    configure_item("Duration (s)##input", enabled=True)
    configure_item("Stimulate", enabled=True)
    configure_item("Send", enabled=True)
    configure_item("End session", enabled=True)
    
# Run stimulation callback
def stimulate_callback(sender, data):
    # Get duration
    dur = get_value("Duration (s)##input")
    
    # Deactivate buttons
    configure_item("Stimulate", enabled=False)
    configure_item("Send", enabled=False)
    configure_item("End session", enabled=False)
    
    # Run stimulation
    device.start()
    time.sleep(dur)
    device.stop()

    # Reactivate buttons
    configure_item("Stimulate", enabled=True)
    configure_item("Send", enabled=True)
    configure_item("End session", enabled=True)

''' Define window layout '''

with window("ONI"):

    ''' Settings window '''
    # Create child object for settings
    with child("SettingsWindow", border=True, width=250, autosize_y=True):
        # Add connect button
        add_text("Connect to Device")
        add_spacing(count=3)
        add_text("")
        add_same_line(xoffset=100)
        add_button("Connect", enabled=True,
                   callback=connect_callback)
        add_spacing(count=3)
        add_separator()

        # Add title
        add_text("Session Control")
        add_spacing(count=3)

        add_spacing(count=3)
        add_text("")
        add_same_line(xoffset=25)
        add_button("Start session", enabled=False,
                   callback=startSession_callback)
        add_same_line()
        add_button("End session", enabled=False,
                   callback=endSession_callback)

        add_spacing(count=3)
        add_separator()

        # Add status section
        add_text("Status")
        add_spacing(count=3)

        # Device status
        add_text("Device:")
        add_same_line(xoffset=75)
        add_label_text("##DeviceStatus", default_value="Not connected", color=[255,0,0])

        # Session details
        add_text("Session:")
        add_same_line(xoffset=75)
        add_label_text("##SessionStatus", default_value="Not started", color=[255,0,0])

        # Overall status
        add_spacing(count=5)
        add_label_text("##OverallStatus", default_value="Ready to connect")

    ''' Sensors window '''
    # Add to same line - i.e. panes arranged horizontally
    add_same_line()

    # Create child object for sensors
    with child("InputWindow", autosize_x=True, autosize_y=True):
        # Add title
        add_text("Waveform:")
        add_spacing(count=3)

        # Add input: waveform
        add_radio_button("Waveform##input", items=["Tonic", "Sinusoidal", "Wavelet", "Offset wavelet"], enabled=False)

        # Add input: frequency
        add_input_int("Frequency (Hz)##input", default_value=0, width=100,
                      enabled=False)

        # Add input: amplitude
        add_input_int("Amplitude (mA)##input", default_value=0, width=100,
                      enabled=False)

        # Add button: stimulate
        add_spacing(count=3)
#        add_text("")
        add_button("Send", enabled=False,
                  callback=send_waveform_callback)

        add_separator()

        # Add waveform section
        add_text("Current waveform")
        add_spacing(count=3)

        add_text("Waveform:")
        add_same_line(xoffset=150)
        add_label_text("##CurrentWaveform", default_value="Not specified")

        add_text("Frequency (Hz):")
        add_same_line(xoffset=150)
        add_label_text("##CurrentFrequency", default_value="Not specified")

        add_text("Amplitude (mA):")
        add_same_line(xoffset=150)
        add_label_text("##CurrentAmplitude", default_value="Not specified")

        # Add input: duration
        add_spacing(count=3)
        add_input_int("Duration (s)##input", default_value=5, width=100,
                      enabled=False)
        add_spacing(count=3)
        add_button("Stimulate", enabled=False,
                   callback=stimulate_callback)

        # Add separator
        add_spacing(count=3)
        add_separator()

''' Start GUI '''

# Function to start GUI
def startGUI():
    # Set main window parameters
    set_main_window_size(1250, 650)
    set_main_window_pos(20, 20)
    set_main_window_title("Oxford Neural Interfacing: Waveform Testing")

    # Start main window
    start_dearpygui(primary_window="ONI")

startGUI()
