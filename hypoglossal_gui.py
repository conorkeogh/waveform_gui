'''
Waveform experiment GUI

Oxford Neural Interfacing
Written by Conor Keogh
conor.keogh@nds.ox.ac.uk
19/03/2024

Graphical interface for data collection from waveform system
Uses custom hardware and drivers
Saves data to file

'''

## Imports
import numpy as np
import time
from threading import Thread

import os.path

from dearpygui.dearpygui import *
create_context()

# Import WaveWriter library
import wavewriter

''' Declare WaveWriter object '''
device = wavewriter.WaveWriter()

class Interface:
    '''
    Contains parameters for determining device state
    Flags:
        dataIn -> controls whether sampler running
        saveData -> controls whether saving data
        inputCheck -> controls whether parameters acceptable

    Methods:
        parseInputs(): loads and checks input parameters
    '''
    def __init__(self):
        self.connected = False    # Whether connected to device
        self.inputCheck = False   # Whether inputs appropriate
        self.ready = False
        self.calibrated = False

        # Number of times to repeat all measures
        self.num_repeats = 3
        
        # Multipliers: output = threshold x multiplier
        self.multiplier_values = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
        self.multiplier_values = np.tile(self.multiplier_values, self.num_repeats)
        self.amplitude_id = 0

        self.NUM_MEASURES = len(self.multiplier_values)
        self.multipliers = np.arange(self.NUM_MEASURES)
        self.measures = np.zeros(self.NUM_MEASURES)

        self.current_amplitude = 50

        # Messages
        self.greeting = b'Hello'
        self.on = b'On\r\n'
        self.off = b'Off\r\n'

    # Parse inputs
    def parseInputs(self):
        '''
        Called when starting session
        Gets values for inputs
        Checks values
        Creates file
        Sets flag to indicate whether OK to continue with current inputs
        '''
        # Get data from inputs
        self.participantID = get_value("Participant##input")
        self.sessionID = get_value("Session ID##input")
        self.sex = get_value("Sex##input")
        self.age = get_value("Age##input")

        # Check inputs
        if self.participantID == '':
            set_value("##OverallStatus", "Enter participant ID")
            self.inputCheck = False
            return
        if self.sessionID == '':
            set_value("##OverallStatus", "Enter session ID")
            self.inputCheck = False
            return
        if self.age == '':
            set_value("##OverallStatus", "Enter age")
            self.inputCheck = False
            return

        if self.sessionID == "Hyomental":
            self.sessionType = 'hyomental'
        elif self.sessionID == "Tongue":
            self.sessionType = 'tongue'

        # Create filepath
        self.filename = self.participantID + '_' + self.sessionType + '.csv'

        # Check if file already exists
        if os.path.exists(self.filename):
            set_value("##OverallStatus", "File already exists")
            self.inputCheck = False
            return

        # If all OK: allow to continue
        self.inputCheck = True

# Create instance
interface = Interface()

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
    interface.connected = True

    # Enable demographic inputs
    configure_item("Participant##input", enabled=True)
    configure_item("Session ID##input", enabled=True)
    configure_item("Age##input", enabled=True)
    configure_item("Sex##input", enabled=True)

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
    interface.parseInputs()

    # If OK: randomise
    if (interface.inputCheck):
        # Reset waveforms and shuffle
        interface.amplitude_id = 0
        np.random.shuffle(interface.multipliers)
    else:
        return

    # Disable all inputs
    configure_item("Participant##input", enabled=False)
    configure_item("Session ID##input", enabled=False)
    configure_item("Age##input", enabled=False)
    configure_item("Sex##input", enabled=False)

    # Reconfigure start -> end session
    configure_item("End session", enabled=True, callback=endSession_callback)
    configure_item("Start session", enabled=False)

    # Update status
    set_value("##SessionStatus", "Started")
    configure_item("##SessionStatus", color=[0,255,0])
    set_value("##OverallStatus", "Session started")

    # Enable running experiment
    configure_item("Load", enabled=True, callback=send_waveform_callback)

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

    # Get data
    participant = get_value("Participant##input")
    session = interface.sessionType
    age = get_value("Age##input")
    sex = get_value("Sex##input")

    baseline = get_value("Baseline (mm)##input")
    threshold_current = get_value("Tolerance threshold (mA)##input")
    threshold_measure = get_value("Measurement (mm)##input")

    # Save data
    with open(interface.filename, 'w') as file:
        # Write header to file
        file.write("Participant ID, session ID, age, sex\n")
        file.write(f"{participant}, {session}, {age}, {sex}\n\n")
        file.write("Amplitude, multiplier, measure\n")
        file.write(f"0, 0.0, {baseline}\n")
        file.write(f"{threshold_current}, 1.0, {threshold_measure}\n")

        # Write data to file
#        for idx in range(interface.NUM_MEASURES):
            #amplitude = int(threshold_current * interface.multiplier_values[interface.multipliers[idx]])
            #file.write(f"{amplitude}, {interface.multiplier_values[interface.multipliers[idx]]}, {interface.measures[interface.multipliers[idx]]}\n")

#        for idx in interface.multipliers:
#            amplitude = int(threshold_current * interface.multiplier_values[idx])
#            multiplier = interface.multiplier_values[idx]
#            val = interface.measures[idx]
#            file.write(f"{amplitude}, {multiplier}, {val}\n")
        for idx in range(interface.NUM_MEASURES):
            val = interface.measures[idx]
            multiplier = interface.multiplier_values[idx]
            amplitude = int(threshold_current * multiplier)
            file.write(f"{amplitude}, {multiplier}, {val}\n")

        file.close()

    # Reset flags
    interface.connected = False
    interface.ready = False
    interface.calibrated = False

    # Re-configure stop -> start session
    configure_item("Connect", enabled=True, callback=connect_callback)
    configure_item("Start session", enabled=False)
    configure_item("End session", enabled=False)

    configure_item("Duration (s)##input", enabled=False)
    configure_item("Load", enabled=False)
    configure_item("Stimulate", enabled=False)

    configure_item("Start", enabled=False)
    configure_item("Baseline (mm)##input", enabled=False)
    configure_item("Tolerance threshold (mA)##input", enabled=False)
    configure_item("Measure (mm)##input", enabled=False)
    configure_item("Measurement (mm)##input", enabled=False)
    configure_item("Next", enabled=False)
    configure_item("Done calibration", enabled=False)

    # Update status
    set_value("##SessionStatus", "Not started")
    configure_item("##SessionStatus", color=[255,0,0])
    set_value("##DeviceStatus", "Not connected")
    configure_item("##DeviceStatus", color=[255,0,0])
    set_value("##OverallStatus", "Ready to connect")

# Stimulate callback
def send_waveform_callback(sender, data):
    send_waveform()
    configure_item("Done calibration", enabled=True)
    configure_item("Load", enabled=False)

def send_waveform():
    '''
    Get data from amplitude and duration fields
    Run stimulation
    '''

    # Get amplitude
    print(interface.current_amplitude)
        
    v, t = wavewriter.generate_wavelet(
        interface.current_amplitude, # mA
        10000, # Hz
        40, # Hz modulating
        4000 # Standard deviation
    )

    # Deactivate stimulate button (if active)
    configure_item("Start", enabled=False)
    configure_item("Stimulate", enabled=False)
    configure_item("Load", enabled=False)
    configure_item("End session", enabled=False)
    configure_item("Next", enabled=False)
    
    # Send waveform
    v, t = wavewriter.convert_waveform(v, t)
    device.send_waveform(v)
    
    # Activate stimulate button
    configure_item("Duration (s)##input", enabled=True)
    configure_item("Stimulate", enabled=True)
    configure_item("Load", enabled=True)
    configure_item("End session", enabled=True)

    configure_item("Start", enabled=True)
    configure_item("Baseline (mm)##input", enabled=True)
    configure_item("Tolerance threshold (mA)##input", enabled=True)
    configure_item("Measure (mm)##input", enabled=True)
    configure_item("Measurement (mm)##input", enabled=True)
    if interface.calibrated:
        configure_item("Next", enabled=True)

    interface.ready = True

# Run stimulation
def start_stimulation_status():
    # Deactivate buttons
    configure_item("Start", enabled=False)
    configure_item("Stop", enabled=True)
    configure_item("Stimulate", enabled=False)
    configure_item("Load", enabled=False)
    configure_item("End session", enabled=False)
    configure_item("Next", enabled=False)
    configure_item("Done calibration", enabled=False)

    set_value("##StimulationStatus", "On")
    configure_item("##StimulationStatus", color=[0,255,0])

def stop_stimulation_status():
    # Reactivate buttons
    configure_item("Start", enabled=True)
    configure_item("Stop", enabled=False)
    configure_item("Stimulate", enabled=True)
    configure_item("Load", enabled=True)
    configure_item("End session", enabled=True)
    if interface.calibrated:
        configure_item("Next", enabled=True)
    else:
        configure_item("Done calibration", enabled=True)

    set_value("##StimulationStatus", "Off")
    configure_item("##StimulationStatus", color=[255,0,0])

def start_stimulation():
    # Update status
    start_stimulation_status()

    # Run stimulation
    device.start()

def stop_stimulation():
    # Stop stimulation
    device.stop()

    # Update status
    stop_stimulation_status()

def start_stimulation_callback(sender, data):
    start_stimulation()

def stop_stimulation_callback(sender, data):
    stop_stimulation()

# Run stimulation callback
def stimulate_callback(sender, data):
    # Get duration
    dur = get_value("Duration (s)##input")
    
    start_stimulation()
    time.sleep(dur)
    stop_stimulation()

# Add measurement callback
def add_measure_callback(sender, data):
    # Get data
    measure = get_value("Measure (mm)##input")

    # Save data
    interface.measures[interface.multipliers[interface.amplitude_id]] = measure

    # Reset values
    interface.amplitude_id += 1
    set_value("##NumMeasures", f"{interface.amplitude_id}")

    # If not at end: send new waveform
    if interface.amplitude_id < interface.NUM_MEASURES:
        # Set new amplitude
        interface.current_amplitude = int(50 * interface.multiplier_values[interface.multipliers[interface.amplitude_id]])

        # Send new amplitude
        send_waveform()

    # If end reached: disable input
    else:
        configure_item("Start session", enabled=False)
        configure_item("End session", enabled=True)

        configure_item("Duration (s)##input", enabled=False)
        configure_item("Load", enabled=False)
        configure_item("Stimulate", enabled=False)

        configure_item("Start", enabled=False)
        configure_item("Baseline (mm)##input", enabled=False)
        configure_item("Tolerance threshold (mA)##input", enabled=False)
        configure_item("Measure (mm)##input", enabled=False)
        configure_item("Measurement (mm)##input", enabled=False)
        configure_item("Next", enabled=False)
        
        # Update overall status
        set_value("##OverallStatus", "Session complete")

# Done calibration callback
def done_calibration_callback(sender, data):
    # Send first amplitude
    interface.current_amplitude = int(50 * interface.multiplier_values[interface.multipliers[interface.amplitude_id]])

    # Send new amplitude
    send_waveform()

    # Enable next button + disable calibration
    configure_item("Next", enabled=True)
    configure_item("Done calibration", enabled=False)

    interface.calibrated = True

# Monitor serial port
def monitor_serial():
    while 1:
        if interface.ready == True:
            response = device.ser.readline()
            if response:
                val = response.decode("utf-8").strip('\x00')#.rstrip('x\00')
                print(val)

                if val == interface.greeting:
                     print("Greeting received")
                elif 'On' in val:
                    start_stimulation_status()
                elif 'Off' in val:
                    stop_stimulation_status()
                else:
                    try:
                        interface.current_amplitude = int(val)
                        set_value("##CurrentAmplitude", f"{interface.current_amplitude}")
                    except:
                        pass
    

''' Define window layout '''

with window(tag="ONI"):

    ''' Settings window '''
    # Create child object for settings
    with child_window(tag="SettingsWindow", parent="ONI", border=True, width=250, autosize_y=True):
        # Add connect button
        add_text("Connect to Device")
        add_spacer(height=3)
        add_text("")
        group(horizontal=True, xoffset=100)
        add_button(label="Connect", tag="Connect", enabled=True,
                   callback=connect_callback)
        add_spacer(height=3)
        add_separator()

        # Add title
        add_text("Session Details")
        add_spacer(height=3)

        # Add input fields
        add_input_text(label="Participant##input", tag="Participant##input", 
                       hint="Enter participant ID",
                      width=150, enabled=False)

        add_radio_button(label="Session ID##input", tag="Session ID##input",
                         items=["Hyomental", "Tongue"],
                         default_value="Hyomental", enabled=False)

        add_input_int(label="Age##input", tag="Age##input", default_value=30, width=100, enabled=False)
        add_text("Sex:")
        group(horizontal=True)
        add_radio_button(label="Sex##input", tag="Sex##input", items=["Male", "Female"], default_value="Male", enabled=False)

        add_spacer(height=3)
        add_text("")
        group(horizontal=True, xoffset=25)
        add_button(label="Start session", tag="Start session", enabled=False,
                   callback=startSession_callback)
        group(horizontal=True)
        add_button(label="End session", tag="End session", enabled=False,
                   callback=endSession_callback)

        add_spacer(height=3)
        add_separator()

        # Add status section
        add_text("Status")
        add_spacer(height=3)

        # Device status
        add_text("Device:")
        group(horizontal=True, xoffset=75)
        add_text("Not connected", label="##DeviceStatus", tag="##DeviceStatus", color=[255,0,0])

        # Session details
        add_text("Session:")
        group(horizontal=True, xoffset=75)
        add_text("Not started", label="##SessionStatus", tag="##SessionStatus", color=[255,0,0])

        # Overall status
        add_spacer(height=5)
        add_text("Ready to connect", label="##OverallStatus", tag="##OverallStatus")

    ''' Sensors window '''
    # Add to same line - i.e. panes arranged horizontally
    group(horizontal=True)

    # Create child object for sensors
    with child_window(label="InputWindow", parent="ONI",
                      before="SettingsWindow", pos=(270,8), autosize_x=True, autosize_y=True, show=True):
        # Add title
        add_text("Waveform:")
        add_spacer(height=3)

        add_button(label="Load", tag="Load", enabled=False,
                  callback=send_waveform_callback)

        add_spacer(height=3)
        add_separator()

        # Add input: duration
        add_spacer(height=3)
        add_text("Run stimulation")
        add_spacer(height=3)
        add_text("Stimulation:")
        group(horizontal=True, xoffset=150)
        add_text("Off", label="##StimulationStatus", tag="##StimulationStatus", color=[255,0,0])
        add_spacer(height=3)

        add_button(label="Start", tag="Start", enabled=False, callback=start_stimulation_callback)
        group(horizontal=True, xoffset=75)
        add_button(label="Stop", tag="Stop", enabled=False, callback=stop_stimulation_callback)
        add_spacer(height=3)
        add_text("Timed stimulation")
        add_input_int(label="Duration (s)##input", tag="Duration (s)##input", default_value=5, width=100,
                      enabled=False)
        add_spacer(height=3)
        add_button(label="Stimulate", tag="Stimulate", enabled=False,
                   callback=stimulate_callback)
        add_spacer(height=3)
        add_separator()

        # Add baseline section
        add_text("Calibration")
        add_spacer(height=3)

        add_text("Max amplitude (mA):")
        group(horizontal=True, xoffset=150)
        add_text(label="##CurrentAmplitude", tag="##CurrentAmplitude", default_value="Not specified")

        add_spacer(height=3)

        add_input_int(label="Baseline (mm)##input", tag="Baseline (mm)##input", default_value=0,
                      width=100, enabled=False)
        add_spacer(height=3)
        add_input_int(label="Tolerance threshold (mA)##input", tag="Tolerance threshold (mA)##input", default_value=0, width=100, enabled=False)
        add_input_int(label="Measurement (mm)##input", tag="Measurement (mm)##input", default_value=0, width=100, enabled=False)

        add_spacer(height=3)
        add_button(label="Done calibration", tag="Done calibration", enabled=False, callback=done_calibration_callback)
        # Add separator
        add_spacer(height=3)
        add_separator()

        # Add data section
        add_text("Data collection")
        add_spacer(height=3)

        add_spacer(height=3)
        add_text("Measurements:")
        group(horizontal=True, xoffset=150)
        add_text(f"{interface.amplitude_id}", label="##NumMeasures", tag="##NumMeasures")
        add_input_int(label="Measure (mm)##input", tag="Measure (mm)##input", default_value=0,
                      width=100, enabled=False)
        add_spacer(height=3)
        add_button(label="Next", tag="Next", enabled=False,
                   callback=add_measure_callback)


''' Start GUI '''

# Function to start GUI
def startGUI():
    # Set main window parameters
    create_viewport(title="Oxford Neural Interfacing: Hypoglossal Testing", width=1250, height=600, x_pos=20, y_pos=20)

    # Start main window
    setup_dearpygui()
    show_viewport()
    set_primary_window("ONI", True)
    start_dearpygui()
    destroy_context()

serialThread = Thread(target=monitor_serial, daemon=True)
serialThread.start()
startGUI()
