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

from dearpygui.core import *
from dearpygui.simple import *

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
        
        self.amplitudes = []
        self.measures = []
        self.num_measures = 0

        self.current_amplitude = 0

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
    configure_item("Waveform##input", enabled=True)
    configure_item("Frequency (Hz)##input", enabled=True)
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

    # Get data
    participant = get_value("Participant##input")
    session = get_value("Session ID##input")
    age = get_value("Age##input")
    sex = get_value("Sex##input")

    pain_threshold = get_value("Pain threshold##input")
    discomfort_threshold = get_value("Discomfort threshold##input")

    # Save data
    with open(interface.filename, 'w') as file:
        # Write header to file
        file.write("Participant ID, session ID, age, sex\n")
        file.write(f"{participant}, {session}, {age}, {sex}\n\n")
        file.write("Discomfort threshold, Pain threshold\n")
        file.write(f"{discomfort_threshold}, {pain_threshold}\n\n")
        file.write("Amplitude, Measurement\n")

        # Write data to file
        for idx in range(interface.num_measures):
            file.write(f"{interface.amplitudes[idx]}, {interface.measures[idx]}\n")

        file.close()

    # Reset flags
    interface.connected = False
    interface.ready = False

    # Re-configure stop -> start session
    configure_item("Connect", enabled=True, callback=connect_callback)
    configure_item("Start session", enabled=False)
    configure_item("End session", enabled=False)

    configure_item("Waveform##input", enabled=False)
    configure_item("Frequency (Hz)##input", enabled=False)
    configure_item("Duration (s)##input", enabled=False)
    configure_item("Send", enabled=False)
    configure_item("Stimulate", enabled=False)

    configure_item("Start", enabled=False)
    configure_item("Discomfort threshold##input", enabled=False)
    configure_item("Pain threshold##input", enabled=False)
    configure_item("Amplitude##input", enabled=False)
    configure_item("Measurement##input", enabled=False)
    configure_item("Save measure", enabled=False)

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
    waveforms = ["Tonic", "Sinusoidal", "Wavelet", "Offset wavelet", "Sawtooth modulated"]
    waveform = waveforms[waveform_id]
    print(waveform)

    # Get frequency
    frequency = get_value("Frequency (Hz)##input")

    # Get amplitude
    amplitude = 50 # Alter on device

    # Send waveform
    print(f"{waveform}: {frequency}Hz")
    
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

    elif waveform == 'Sawtooth modulated':
        v, t = wavewriter.generate_sawtooth_modulated(
            amplitude, # mA
            frequency, # Hz
            20 # Hz modulating
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
    set_value("##CurrentAmplitude", f"{interface.current_amplitude}")
    
    # Activate stimulate button
    configure_item("Duration (s)##input", enabled=True)
    configure_item("Stimulate", enabled=True)
    configure_item("Send", enabled=True)
    configure_item("End session", enabled=True)

    configure_item("Start", enabled=True)
    configure_item("Discomfort threshold##input", enabled=True)
    configure_item("Pain threshold##input", enabled=True)
    configure_item("Amplitude##input", enabled=True)
    configure_item("Measurement##input", enabled=True)
    configure_item("Save measure", enabled=True)

    interface.ready = True

# Run stimulation
def start_stimulation_status():
    # Deactivate buttons
    configure_item("Start", enabled=False)
    configure_item("Stop", enabled=True)
    configure_item("Stimulate", enabled=False)
    configure_item("Send", enabled=False)
    configure_item("End session", enabled=False)

    set_value("##StimulationStatus", "On")
    configure_item("##StimulationStatus", color=[0,255,0])

def stop_stimulation_status():
    # Reactivate buttons
    configure_item("Start", enabled=True)
    configure_item("Stop", enabled=False)
    configure_item("Stimulate", enabled=True)
    configure_item("Send", enabled=True)
    configure_item("End session", enabled=True)

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
    amplitude = get_value("Amplitude##input")
    measure = get_value("Measurement##input")

    # Save data
    interface.amplitudes.append(amplitude)
    interface.measures.append(measure)

    # Reset values
    interface.num_measures += 1
    set_value("##NumMeasures", f"{interface.num_measures}")

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
        add_spacing(count=3)

        # Add input: waveform
        add_radio_button("Waveform##input", items=["Tonic", "Sinusoidal",
                                                   "Wavelet", "Offset wavelet",
                                                  "Sawtooth modulated"], enabled=False)

        # Add input: frequency
        add_input_int("Frequency (Hz)##input", default_value=0, width=100,
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
        add_spacing(count=3)

        add_text("Stimulation:")
        add_same_line(xoffset=150)
        add_label_text("##StimulationStatus", default_value="Off", color=[255,0,0])

        add_text("Amplitude (mA):")
        add_same_line(xoffset=150)
        add_label_text("##CurrentAmplitude", default_value="Not specified")

        # Add input: duration
        add_spacing(count=3)
        add_text("Run stimulation")
        add_button("Start", enabled=False, callback=start_stimulation_callback)
        add_same_line(xoffset=75)
        add_button("Stop", enabled=False, callback=stop_stimulation_callback)
        add_spacing(count=3)
        add_text("Timed stimulation")
        add_input_int("Duration (s)##input", default_value=5, width=100,
                      enabled=False)
        add_spacing(count=3)
        add_button("Stimulate", enabled=False,
                   callback=stimulate_callback)

        # Add separator
        add_spacing(count=3)
        add_separator()

        # Add data section
        add_text("Data collection")
        add_spacing(count=3)

        add_input_int("Discomfort threshold##input", default_value=0,
                      width=100, enabled=False)
        add_input_int("Pain threshold##input", default_value=0, width=100,
                      enabled=False)

        add_spacing(count=3)
        add_input_int("Amplitude##input", default_value=0, width=100,
                      enabled=False)
        add_input_int("Measurement##input", default_value=0, width=100,
                      enabled=False)
        add_spacing(count=3)
        add_text("Measurements:")
        add_same_line(xoffset=120)
        add_label_text("##NumMeasures", default_value=f"{interface.num_measures}")
        add_spacing(count=3)
        add_button("Save measure", enabled=False,
                   callback=add_measure_callback)

''' Start GUI '''

# Function to start GUI
def startGUI():
    # Set main window parameters
    set_main_window_size(1250, 650)
    set_main_window_pos(20, 20)
    set_main_window_title("Oxford Neural Interfacing: Waveform Testing")

    # Start main window
    start_dearpygui(primary_window="ONI")

serialThread = Thread(target=monitor_serial, daemon=True)
serialThread.start()
startGUI()
