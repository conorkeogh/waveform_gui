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
    - Enter participant details
    - Randomise waveforms
    - For each: enter thresholds
    - Save data
    - Documentation
    - Run from command line

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

''' Define waveforms '''
NUM_WAVEFORMS = 8
waveform_id = 0

''' Randomise waveforms '''

''' Define interface state '''

class Interface:
    '''
    Contains parameters for determining device state
    Flags:
        dataIn -> controls whether sampler running
        saveData -> controls whether saving data
        inputCheck -> controls whether parameters acceptable
        doUpdate -> controls whether to update plots

    Methods:
        parseInputs(): loads and checks input parameters
    '''
    def __init__(self):
        self.connected = False    # Whether connected to device
        self.inputCheck = False   # Whether inputs appropriate
        self.waveform_id = 0
        self.NUM_WAVEFORMS = 8
        self.waveforms = np.arange(NUM_WAVEFORMS)
        self.waveform_titles = [
            'Tonic', 'Nevro HF', 'Abbott Burst', 'Boston Burst',
            'Sinusoidal', 'Russian', 'Wavelet', 'Offset wavelet'
        ]

        self.thresholds_perception = np.zeros(NUM_WAVEFORMS)
        self.thresholds_sensory = np.zeros(NUM_WAVEFORMS)
        self.thresholds_motor = np.zeros(NUM_WAVEFORMS)
        self.thresholds_discomfort = np.zeros(NUM_WAVEFORMS)
        self.thresholds_pain = np.zeros(NUM_WAVEFORMS)
        
        self.pain_scores = np.zeros(NUM_WAVEFORMS)
        self.electrode_pain = np.zeros(NUM_WAVEFORMS)
        self.paraesthesia_pain = np.zeros(NUM_WAVEFORMS)
        self.motor_pain = np.zeros(NUM_WAVEFORMS)

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

        # Create filepath
        self.filename = self.participantID + '_' + self.sessionID + '.csv'

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
    Enables demographic data input
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

    # If session parameters OK, proceed to state change
    if (interface.inputCheck):
        # Reset waveforms and shuffle
        interface.waveform_id = 0
        np.random.shuffle(interface.waveforms) 

    # Otherwise, set an error and stop here
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
    configure_item("Amplitude (mA)##input", enabled=True)
    configure_item("Duration (s)##input", enabled=True)
    configure_item("Send", enabled=True, callback=send_waveform_callback)
    configure_item("Stimulate", enabled=False)

    configure_item("Perception##input", enabled=True)
    configure_item("Sensory##input", enabled=True)
    configure_item("Motor##input", enabled=True)
    configure_item("Discomfort##input", enabled=True)
    configure_item("Pain##input", enabled=True)
    
    configure_item("Pain rating##input", enabled=True)
    configure_item("Electrode pain##input", enabled=True)
    configure_item("Paraesthesia pain##input", enabled=True)
    configure_item("Motor pain##input", enabled=True)

    configure_item("Next waveform", enabled=True,
                   callback=nextWaveform_callback)

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
    print(f"{type(interface.waveforms)}, {type(interface.thresholds_perception)}, {type(interface.thresholds_sensory)}, {type(interface.thresholds_motor)}, {type(interface.thresholds_discomfort)}, {type(interface.thresholds_pain)}")

    # Save all data
    # Write header to file
    with open(interface.filename, 'w') as file:
        # Write header to file
        file.write("Waveform, Perception, Sensory, Motor, Discomfort, Pain, Pain Score, Electrode Pain, Paraesthesia Pain, Motor Pain\n")

        # Write data to file
        for idx in range(NUM_WAVEFORMS):
            file.write(f"{interface.waveform_titles[idx]}, {interface.thresholds_perception[idx]}, {interface.thresholds_sensory[idx]}, {interface.thresholds_motor[idx]}, {interface.thresholds_discomfort[idx]}, {interface.thresholds_pain[idx]}, {interface.pain_scores[idx]}, {interface.electrode_pain[idx]}, {interface.paraesthesia_pain[idx]}, {interface.motor_pain[idx]}\n")

        file.close()

    # Reset flags
    interface.connected = False

    # Re-enable inputs
    configure_item("Participant##input", enabled=False)
    configure_item("Session ID##input", enabled=False)
    configure_item("Age##input", enabled=False)
    configure_item("Sex##input", enabled=False)

    # Re-configure stop -> start session
    configure_item("Connect", enabled=True, callback=connect_callback)
    configure_item("Start session", enabled=False)
    configure_item("End session", enabled=False)

    configure_item("Amplitude (mA)##input", enabled=False)
    configure_item("Duration (s)##input", enabled=False)
    configure_item("Send", enabled=False)
    configure_item("Stimulate", enabled=False)

    configure_item("Perception##input", enabled=False)
    configure_item("Sensory##input", enabled=False)
    configure_item("Motor##input", enabled=False)
    configure_item("Discomfort##input", enabled=False)
    configure_item("Pain##input", enabled=False)
    
    configure_item("Pain rating##input", enabled=False)
    configure_item("Electrode pain##input", enabled=False)
    configure_item("Paraesthesia pain##input", enabled=False)
    configure_item("Motor pain##input", enabled=False)

    configure_item("Next waveform", enabled=False)

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
    # Get amplitude
    amplitude = get_value("Amplitude (mA)##input")

    # Send waveform
        # Use waveforms[waveform_id] to determine which waveform to generate
        # e.g. switch/case using this to determine which function to run
    current_waveform = interface.waveforms[interface.waveform_id]
    
    if interface.waveform_titles[current_waveform] == 'Tonic':
        v, t = wavewriter.generate_tonic(
            amplitude, # mA
            40, # Hz
            100, # us
            biphasic = True
        )
        
    elif interface.waveform_titles[current_waveform] == 'Nevro HF':
        v, t = wavewriter.generate_tonic(
            amplitude, # mA
            10000, # Hz
            30, # us
            biphasic = True
        )
        
    elif interface.waveform_titles[current_waveform] == 'Boston Burst':
        v, t = wavewriter.generate_burst_boston(
            amplitude, # mA
            5, # Pulses per burst
            500, # Hz intraburst
            40, # Hz interburst
            1000 # us pulsewidth
        )
        
    elif interface.waveform_titles[current_waveform] == 'Abbott Burst':
        v, t = wavewriter.generate_burst_abbott(
            amplitude, # mA
            500, # Hz intraburst
            40, # Hz interburst
            1000, # us pulsewidth
        )
        
    elif interface.waveform_titles[current_waveform] == 'Sinusoidal':
        v, t = wavewriter.generate_sine(
            amplitude, # mA
            2000, # Hz
            1 # Cycles
        )
        
    elif interface.waveform_titles[current_waveform] == 'Russian':
        v, t = wavewriter.generate_russian(
            amplitude, # mA
            2000, # Hz
            40, # Hz (modulating)
            10000 # us window length
        )
        
    elif interface.waveform_titles[current_waveform] == 'Wavelet':
        v, t = wavewriter.generate_wavelet(
            amplitude, # mA
            2000, # Hz
            40, # Hz modulating
            4000 # Standard deviation
        )
        
    elif interface.waveform_titles[current_waveform] == 'Offset wavelet':
        v, t = wavewriter.generate_wavelet_modulated(
            amplitude, # mA
            2000, # Hz
            40, # Hz modulating
            4000, # Standard deviation
        )

    
    # Deactivate stimulate button (if active)
    configure_item("Stimulate", enabled=False)
    configure_item("Send", enabled=False)
    configure_item("End session", enabled=False)
    configure_item("Next waveform", enabled=False)
    
    # Send waveform
    v, t = wavewriter.convert_waveform(v, t)
    device.send_waveform(v)
    
    # Activate stimulate button
    configure_item("Stimulate", enabled=True)
    configure_item("Send", enabled=True)
    configure_item("End session", enabled=True)
    configure_item("Next waveform", enabled=True)
    
# Run stimulation callback
def stimulate_callback(sender, data):
    # Get duration
    dur = get_value("Duration (s)##input")
    
    # Deactivate buttons
    configure_item("Stimulate", enabled=False)
    configure_item("Send", enabled=False)
    configure_item("End session", enabled=False)
    configure_item("Next waveform", enabled=False)
    
    # Run stimulation
    device.start()
    time.sleep(dur)
    device.stop()

    # Reactivate buttons
    configure_item("Stimulate", enabled=True)
    configure_item("Send", enabled=True)
    configure_item("End session", enabled=True)
    configure_item("Next waveform", enabled=True)
    
# Next waveform callback
def nextWaveform_callback(sender, data):
    '''
    Move to next waveform
    Save threshold data
    Update waveform display
    Load next waveform
    '''
    # Get threshold data
    interface.thresholds_perception[interface.waveforms[interface.waveform_id]] = get_value("Perception##input")
    interface.thresholds_sensory[interface.waveforms[interface.waveform_id]] = get_value("Sensory##input")
    interface.thresholds_motor[interface.waveforms[interface.waveform_id]] = get_value("Motor##input")
    interface.thresholds_discomfort[interface.waveforms[interface.waveform_id]] = get_value("Discomfort##input")
    interface.thresholds_pain[interface.waveforms[interface.waveform_id]] = get_value("Pain##input")
    
    interface.pain_scores[interface.waveforms[interface.waveform_id]] = get_value("Pain rating##input")
    interface.electrode_pain[interface.waveforms[interface.waveform_id]] = get_value("Electrode pain##input")
    interface.paraesthesia_pain[interface.waveforms[interface.waveform_id]] = get_value("Paraesthesia pain##input")
    interface.motor_pain[interface.waveforms[interface.waveform_id]] = get_value("Motor pain##input")

    # Move to next waveform
    interface.waveform_id += 1

    # If end reached: disable buttons and inputs, update status
    if interface.waveform_id >= NUM_WAVEFORMS:
        # Disable inputs
        configure_item("Amplitude (mA)##input", enabled=False)
        configure_item("Duration (s)##input", enabled=False)
        configure_item("Send", enabled=False)
        configure_item("Stimulate", enabled=False)

        configure_item("Perception##input", enabled=False)
        configure_item("Sensory##input", enabled=False)
        configure_item("Motor##input", enabled=False)
        configure_item("Discomfort##input", enabled=False)
        configure_item("Pain##input", enabled=False)
    
        configure_item("Pain rating##input", enabled=False)
        configure_item("Electrode pain##input", enabled=False)
        configure_item("Paraesthesia pain##input", enabled=False)
        configure_item("Motor pain##input", enabled=False)

        configure_item("Next waveform", enabled=False)

        # Update overall status
        set_value("##OverallStatus", "Session complete")

    else:
        # Update display
        set_value("##WaveformStatus", f"{interface.waveform_id+1}")
        configure_item("Send", enabled=True)
        configure_item("Stimulate", enabled=False)

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
        add_text("Session Details")
        add_spacing(count=3)

        # Add input fields
        add_input_text("Participant##input", 
                       hint="Enter participant ID",
                      width=150, enabled=False)

        add_input_text("Session ID##input", hint="Enter session ID",
                       width=150, enabled=False)

        add_input_int("Age##input", default_value=30, width=100, enabled=False)
        add_text("Sex:")
        add_same_line()
        add_radio_button("Sex##input", items=["Male", "Female"], enabled=False)

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
        add_same_line(xoffset=75)
        add_label_text("##WaveformStatus", default_value=f"{waveform_id+1}",
                       color=[255,255,255])
        add_spacing(count=3)

        # Add input: amplitude
        add_input_int("Amplitude (mA)##input", default_value=0, width=100,
                      enabled=False)

        # Add input: duration
        add_input_int("Duration (s)##input", default_value=5, width=100,
                      enabled=False)

        # Add button: stimulate
        add_spacing(count=3)
#        add_text("")
        add_button("Send", enabled=False,
                  callback=send_waveform_callback)
        add_same_line()
        add_button("Stimulate", enabled=False,
                   callback=stimulate_callback)

        # Add separator
        add_spacing(count=3)
        add_separator()

        # Add inputs: thresholds
        add_text("Thresholds (mA)")
        add_spacing(count=3)

        # Add input fields
        add_input_int("Perception##input", default_value=0, width=100,
                      enabled=False)
        add_input_int("Sensory##input", default_value=0, width=100,
                      enabled=False)
        add_input_int("Motor##input", default_value=0, width=100, enabled=False)
        add_input_int("Discomfort##input", default_value=0, width=100,
                      enabled=False)
        add_input_int("Pain##input", default_value=0, width=100, enabled=False)

        # Add button: next
        add_spacing(count=3)
        add_input_int("Pain rating##input", default_value=0, width=100, enabled=False)
        add_input_int("Electrode pain##input", default_value=0, width=100, enabled=False)
        add_input_int("Paraesthesia pain##input", default_value=0, width=100, enabled=False)
        add_input_int("Motor pain##input", default_value=0, width=100, enabled=False)

        add_spacing(count=3)
        #add_text("")
        #add_same_line(xoffset=25)
        add_button("Next waveform", enabled=False,
                   callback=nextWaveform_callback)

''' Start GUI '''

# Function to start GUI
def startGUI():
    # Set main window parameters
    set_main_window_size(1250, 650)
    set_main_window_pos(20, 20)
    set_main_window_title("Oxford Neural Interfacing: Waveform Testing")

    # Start main window
    start_dearpygui(primary_window="ONI")

# Start system
'''
plotThread = Thread(target=runUpdatePlots, daemon=True)
plotThread.start()

dataThread = Thread(target=collectData, daemon=True)
dataThread.start()

structThread = Thread(target=updateStructures, daemon=True)
structThread.start()
'''
startGUI()
