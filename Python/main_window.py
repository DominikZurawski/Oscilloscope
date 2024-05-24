# standard imports #
import sys											# deal with OS, open files and so
import time 										# delays, and time measurement ?
import random										# random numbers
import os											# dealing with directories

import serial										# required to handle serial communication
import serial.tools.list_ports						# to list already existing ports

import csv
import numpy as np 									# required to handle multidimensional arrays/matrices

import threading
import matplotlib.pyplot as plt

import logging
#logging.basicConfig(level=logging.DEBUG)			# enable debug messages
from future.utils import text_type

logging.basicConfig(level = logging.WARNING)

# custom packages #

from pyqt_common_resources import pyqt_custom_palettes				# moved to an independent repo, to reuse the palettes.
from my_graph import MyPlot
import my_graph														# for the global variables of the namespace.
from range_dialog import RangeDialog

# qt imports #
from PyQt5.QtWidgets import (
	QApplication,
	QMainWindow,
	QVBoxLayout,
	QHBoxLayout,
	QLabel,
	QComboBox,
	QLineEdit,
	QPushButton,
	QMenuBar,
	QToolBar,
	QStatusBar,
	QDialog,
	QMessageBox,														# Dialog with extended functionality. 
	QShortcut,
	QCheckBox,	

	QSystemTrayIcon,
	QTextEdit,
	QMenu,
	QAction,
	QWidget,
	QInputDialog,
)

from PyQt5.QtGui import (
	QIcon,
	QKeySequence
)

from PyQt5.QtCore import(
	Qt,
	QThreadPool,
	QRunnable,
	QObject,
	QSize,
	pyqtSignal,															# those two are pyqt specific. 
	pyqtSlot,
	QTimer																# nasty stuff

)

# GLOBAL VARIABLES #

K = 3.3 / 4096 	# ADC to voltage conversion converter
Fs = 1000  # Przykładowa częstotliwość próbkowania (1 kHz)							
czas_zbierania = 10  # w sekundach # Określenie długości próbki na podstawie czasu zbierania (np. 10 sekund)
n = int(Fs * czas_zbierania)							
Ts = 1 / Fs		 # Częstotliwość próbkowania (Ts)										
t = np.linspace(0, czas_zbierania, n)  # Tworzenie wektora czasu


SERIAL_BUFFER_SIZE = 10000												# buffer size to store the incoming data from serial, to afterwards process it.
SEPARATOR = "----------------------------------------------------------"


SERIAL_SPEEDS = [
	"300",
	"1200",
	"2400",
	"4800",
	"9600",
	"19200",
	"38400",
	"57600",
	"74880",
	"115200",
	"230400",
	"250000",
	"500000",
	"1000000",
	"2000000"
]

ENDLINE_OPTIONS = [
	"No Line Adjust",
	"New Line",
	"Carriage Return",
	"Both NL & CR"
]

RECORD_PERIOD = 1000 													# time in ms between two savings of the recorded data onto file
POINTS_PER_PLOT = 3000													# width of x axis, corresponding to the number of dots to be plotted at each iteration

# THREAD STUFF #  (not needed ATM)

		
# MAIN WINDOW #			

class MainWindow(QMainWindow): 
	
	# class variables #
	serial_ports = list													# list of serial ports detected, probably this is better somewhere else !!!
	serial_port = None													# maybe better to decleare it somewhere else ??? serial port used for the comm.
	serial_port_name = None												# used to pass it to the worker dealing with the serial port.
	serial_baudrate = 115200											# default baudrate, ALL THOSE VARIABLES SHOULD CONNECT TO WORKER_SERIALPORT!
	endline = '\r\n'													# default value for endline is CR+NL 
	error_type = None													# used to try to fix the problem with dialog window, delete if can't fix !!!
	serial_message_to_send = None										# if not none, is a message to be sent via serial port (the worker sends)
	full_screen_flag = False
	dataset = []														# dataset containing the data to be plotter/recorded.
	log_folder = "logs"													# in the beginning, log folder, path and filename are fixed
	log_file_name = "log_file"											# at some point, path needs to be selected by user.
	log_file_type = ".csv"												# file extension
	n_logs = 0 
	log_full_path = None												# this variable will be the one used to record 
	timeouts = 0
	parsing_style = "Microcontroller"											# defines the parsing style, for now Microcontroller, or EMG
	read_buffer = ""													# if change to default parsing emg style: read_buffer = [], all chars read from serial come here, should it go somewhere else?
	recording = False													# flag to start/stop recording.
	first_toggles = 0													# used to check the toggles which contain data on start graphing.
	n_data_points = POINTS_PER_PLOT										# defaults to the POINTS_PER_PLOT value
	
	# constructor # 
	def __init__(self):
				
		super().__init__()
		
		self.init_dataset()

		self.plot_frame = MyPlot(dataset = self.dataset, 
									max_points = self.n_data_points)		# we'll use a custom class, so we can modify the defaults via class definition

		# timer to record data onto file periodically (DELETES OLD DATA IF RECORD NOT ENABLED)#
		self.record_timer = QTimer()
		self.record_timer.timeout.connect(self.on_record_timer)			# will be enabled / disabled via button
		self.record_timer.start(RECORD_PERIOD)							# deploys data onto file once a second
		self.record_timer.stop()
		# serial timer #
		self.serial_timer = QTimer()									# we'll use timer instead of thread
		self.serial_timer.timeout.connect(self.on_serial_timer)		
		self.serial_timer.start(50)										# period needs to be relatively short
		self.serial_timer.stop()										# by default the timer will be off, enabled by connect.
		# update serial ports timer #
		self.update_ports_timer = QTimer()
		self.update_ports_timer.timeout.connect(
			self.update_serial_ports)									# updating serial port list in a regular time basis. 
		self.update_ports_timer.start(200)								# every  3 seconds seems reasonable.
		self.update_ports_timer.stop()
			

		# shortcuts moved to the bottom #

		# theme(palette) #
		self.palette = pyqt_custom_palettes.dark_palette()
		self.setPalette(self.palette)
		
		# window stuff #
		self.setWindowTitle("MScope")					# relevant title
		self.setWindowIcon(QIcon("RE_logo_32p.png"))					# basic raquena engineering branding
		self.resize(1200,800)											# setting initial window size
		# menubar #
		menu = self.menuBar()											# by default, the window already has an instance/object menubar
		# file #
		self.file_menu = menu.addMenu("&File")
		self.serial_port_menu = self.file_menu.addMenu("Serial Port")
		self.refresh_menu = self.file_menu.addAction("Refresh")
		self.refresh_menu.triggered.connect(self.update_serial_ports)
		# Preferences #
		self.preferences_menu = menu.addMenu("&Preferences")
		# theme #
		self.theme_submenu = self.preferences_menu.addMenu("Theme")
		self.dark_theme_option = self.theme_submenu.addAction("Dark")
		self.dark_theme_option.triggered.connect(self.set_dark_theme)
		self.light_theme_option = self.theme_submenu.addAction("Light")
		self.light_theme_option.triggered.connect(self.set_light_theme)
		self.re_theme_option = self.theme_submenu.addAction("Raquena")
		self.re_theme_option.triggered.connect(self.set_re_theme)
		# Parsing #
		self.parsing_submenu = self.preferences_menu.addMenu("Parsing mode")
		self.Microcontroller_parsing_option = self.parsing_submenu.addAction("Microcontroller")
		self.Microcontroller_parsing_option.triggered.connect(self.set_Microcontroller_parsing)
		self.emg_parsing_option = self.parsing_submenu.addAction("EMG Sensor")
		self.emg_parsing_option.triggered.connect(self.set_emg_parsing)
		self.emg_parsing_new_option = self.parsing_submenu.addAction("EMG Sensor NEW")
		self.emg_parsing_new_option.triggered.connect(self.set_emg_parsing_new)
		# Set plot range #
		self.set_range_action = self.preferences_menu.addAction("Set Plot Y Range")
		self.set_range_action.triggered.connect(self.set_plot_range)
		# Set maximum plot points #
		self.set_n_plot_points_action = self.preferences_menu.addAction("Set max. plot points (X Range)")
		self.set_n_plot_points_action.triggered.connect(self.set_n_plot_points)

		# about #
		help_menu = menu.addMenu("&Help")
		about_menu = help_menu.addAction("About")
		
		button_action = QAction()
		self.file_menu.addAction(button_action)
		
		#self.toolbar.setIconSize(Qsize(16,16))
		#self.addToolBar(self.toolbar)
		#self.menubar.addMenu("&file")
		
		# central widget #
		self.widget = QWidget()
		self.layoutV1 = QVBoxLayout()									# that's how we will lay out the window
		self.widget.setLayout(self.layoutV1)
		self.setCentralWidget(self.widget)							
		# graph / plot #
		self.layout_plot = QHBoxLayout()								# plot plus buttons to enable/disable graphs
		self.layoutV1.addLayout(self.layout_plot)
		
		self.plot_frame.max_points = self.n_data_points					# width of the plot in points, doesn't work !!!
		self.plot_frame.enable_toggles("none")
		self.plot_frame.check_toggles("none")		
		self.layout_plot.addWidget(self.plot_frame)
		# buttons for plot #
		self.layout_player = QHBoxLayout()
		self.layoutV1.addLayout(self.layout_player)
		# play button # 
		self.button_play = QPushButton("Play")
		self.button_play.setIcon(QIcon('resources/player_icons/131.png'))
		self.button_play.clicked.connect(self.on_button_play)
		self.button_play.setEnabled(False)
		self.layout_player.addWidget(self.button_play)
		# pause button # 
		self.button_pause = QPushButton("Pause")
		self.button_pause.setIcon(QIcon('resources/player_icons/141.png'))
		self.button_pause.clicked.connect(self.on_button_pause)
		self.button_pause.setEnabled(False)
		self.layout_player.addWidget(self.button_pause)
		# record button # 
		self.button_record = QPushButton("Record")
		self.button_record.setIcon(QIcon('resources/player_icons/148.png'))
		self.button_record.clicked.connect(self.on_button_record)		# enables timer to periodically store the data onto a file. 
		self.layout_player.addWidget(self.button_record)		
		# stop button # 
		self.button_stop = QPushButton("Stop")
		self.button_stop.setIcon(QIcon('resources/player_icons/142.png'))
		self.button_stop.clicked.connect(self.on_button_stop)			# enables timer to periodically store the data onto a file. 
		self.button_stop.setEnabled(False)
		self.layout_player.addWidget(self.button_stop)
		# autoscale #
		self.button_autoscale = QPushButton("Autoscale")
		self.button_autoscale.setIcon(QIcon('resources/player_icons/195.png'))
		self.button_autoscale.clicked.connect(self.on_button_autoscale)
		self.layout_player.addWidget(self.button_autoscale)
		#self.button_autoscale.setCheckable(True)

		# ~ self.autoscale_toggle = LabelledAnimatedToggle(color = "#ffffff",label_text = "Autoscale")
		# ~ self.layout_player.addWidget(self.autoscale_toggle)
				
				
		# buttons / menus # 
		self.layoutH1 = QHBoxLayout()
		self.layoutV1.addLayout(self.layoutH1)
		# connect button #
		self.button_serial_connect = QPushButton("Connect")
		self.button_serial_connect.clicked.connect(self.on_button_connect_click)
		self.layoutH1.addWidget(self.button_serial_connect)
		# disconnect button #
		self.button_serial_disconnect = QPushButton("Disconnect")
		self.button_serial_disconnect.clicked.connect(self.on_button_disconnect_click)
		self.button_serial_disconnect.setEnabled(False)
		self.layoutH1.addWidget(self.button_serial_disconnect)
		# combo serial port #
		self.combo_serial_port = QComboBox()
		self.layoutH1.addWidget(self.combo_serial_port)
		self.update_serial_ports()
		self.combo_serial_port.currentTextChanged.connect(				# changing something at this label, triggers on_port select, which should trigger a serial port characteristics update.
			self.on_port_select)
		self.label_port = QLabel("Port")
		self.layoutH1.addWidget(self.label_port)
		# combo serial speed #
		self.combo_serial_speed = QComboBox()
		self.combo_serial_speed.setEditable(False)						# by default it isn't editable, but just in case.
		self.combo_serial_speed.addItems(SERIAL_SPEEDS)
		self.combo_serial_speed.setCurrentIndex(SERIAL_SPEEDS.index(str(self.serial_baudrate)))						# this index corresponds to 250000 as default baudrate.
		self.combo_serial_speed.currentTextChanged.connect(				# on change on the serial speed textbox, we call the connected mthod
			self.change_serial_speed) 									# we'll figure out which is the serial speed at the method (would be possible to use a lambda?) 
		self.layoutH1.addWidget(self.combo_serial_speed)				# 
		self.label_baud = QLabel("baud")
		self.layoutH1.addWidget(self.label_baud)
		# text box command #
		self.textbox_send_command = QLineEdit()
		self.textbox_send_command.returnPressed.connect(self.send_serial)	# sends command via serial port
		self.textbox_send_command.setEnabled(False)						# not enabled until serial port is connected. 
		self.layoutH1.addWidget(self.textbox_send_command)
		# send button # 
		self.b_send = QPushButton("Send")											
		self.b_send.clicked.connect(self.send_serial)					# same action as enter in textbox
		self.layoutH1.addWidget(self.b_send)
		# combo endline #
		self.combo_endline_params = QComboBox()
		self.combo_endline_params.addItems(ENDLINE_OPTIONS)
		self.combo_endline_params.setCurrentIndex(3)					# defaults to endline with CR & NL
		self.combo_endline_params.currentTextChanged.connect(self.change_endline_style)
		self.layoutH1.addWidget(self.combo_endline_params)
		
		# status bar #
		self.status_bar = QStatusBar()
		self.setStatusBar(self.status_bar)
		self.status_bar.showMessage("Not Connected")
		# 3. write text saying no serial port is connected
		
		# show and done #		
		self.show()
		
		# other stuff which can't be done before #
		self.serial_port_name = self.combo_serial_port.currentText()
		self.serial_baudrate = int(self.combo_serial_speed.currentText())	
		# self.serial_baudrate = ...
		# self.endline = ...

		self.maxsimum = [0,0]
		self.minimum = [1000,1000]
		

	# on close #
		
	def closeEvent(self, event):

		print("CLOSING AND CLEANING UP:")
		try:
			print("Closing serial port")
			self.serial_port.close()										# need to explicitly close the serial port to release it
		except:
			print("Couldn't close serial port, probably already closed / never open")
		super().close()
		#event.ignore()													# extremely useful to ignore the close event !
	
	# actions #		
	
	def set_logfile(self):	
		# 1. be sure the folder where the log file should be placed exists
		# logs folder #
		print("Log file name:")
		print(self.log_file_name)
		print("Log file folder:")
		print(self.log_folder)
		
		if not os.path.exists(self.log_folder):							# create logs folder to store the logs
			os.makedirs(self.log_folder)								# mkdir only makes one directory on the path, makedirs, makes all
		# 2. check what's on that folder.
		path = os.getcwd()
		print("current path:")
		print(path)
		fullpath = path +'/'+ self.log_folder +'/'+ self.log_file_name + self.log_file_type
		print("Full file path")
		print(fullpath)
		if os.path.exists(fullpath):
			fullpath = path +'/'+ self.log_folder +'/'+ self.log_file_name + str(self.n_logs) + self.log_file_type
			self.n_logs = self.n_logs + 1
		
		self.log_full_path = fullpath;
	
		
	def send_serial(self, command = None):										# if no command, we get text from textbox, if command, we send what we got internally
		logging.debug("Send Serial")
		if(command == None):
			command = self.textbox_send_command.text()								# get what's on the textbox.
			self.textbox_send_command.setText("")
		# here the serial send command # 
		self.serial_message_to_send = command.encode('utf-8')					# this should have effect on the serial_thread

		logging.debug("serial_message_to_send")
		logging.debug(self.serial_message_to_send)
		self.serial_port.write(self.serial_message_to_send)
	
	# other methods # 
		
	def get_serial_ports(self):			# REWRITE THIS FUNCTION TO USE A DICTIONARY, AND MAKE IT WAY CLEANER !!!
				
		logging.debug('Running get_serial_ports')
		serial_port = None
		self.serial_ports = list(serial.tools.list_ports.comports())	# THIS IS THE ONLY PLACE WHERE THE OS SERIAL PORT LIST IS READ. 	
		
		port_names = []		# we store all port names in this variable
		port_descs = []		# all descriptions
		port_btenums = []	# all bluetooth enumerations, if proceeds
		for port in self.serial_ports:
			port_names.append(port[0])	# here all names get stored
			port_descs.append(port[1])
			port_btenums.append(port[2])
			
		for name in port_names:
			logging.debug(name)
		logging.debug("---------------------------------------------------")

		for desc in port_descs:
			logging.debug(desc)
		logging.debug("---------------------------------------------------")

		for btenum in port_btenums:
			logging.debug(btenum)
		logging.debug("---------------------------------------------------")
						
		# remove bad BT ports (windows creates 2 ports, only one is useful to connect)
		
		for port in self.serial_ports:
			
			port_desc = port[1]
			
			if (port_desc.find("Bluetooth") != -1):						# Bluetooth found on description,so is a BT port (good or bad, dunno yet)
				
				# Using the description as the bt serial ports to find out the "good" bluetooth port.
				port_btenum = port[2]
				port_btenum = str(port_btenum)
				splitted_enum = port_btenum.split('&')
				logging.debug(splitted_enum)							# uncomment this to see why this parameter was used to differentiate bt ports.
				last_param = splitted_enum[-1]							# this contains the last parameter of the bt info, which is different between incoming and outgoing bt serial ports. 
				last_field = last_param.split('_')						# here there is the real difference between the two created com ports
				last_field = last_field[-1]								# we get only the part after the '_'
				logging.debug(last_field)
				
				if(last_field == "C00000000"):							# this special string is what defines what are the valid COM ports.
					discarded = 0										# the non-valid COM ports have a field liked this: "00000001", and subsequent.
				else:
					discarded = 1
					logging.debug("This port should be discarded!")
					self.serial_ports.remove(port)						# removes by matching description
		
	def change_serial_speed(self):										# this function is useless ATM, as the value is asked when serial open again.
		logging.debug("change_serial_speed method called")
		text_baud = self.combo_serial_speed.currentText()
		baudrate = int(text_baud)
		#self.serial_port.baudrate.set(baudrate)	
		self.serial_baudrate = baudrate			
		logging.debug(text_baud)
		
	def change_endline_style(self):										# this and previous method are the same, use lambdas?
		logging.debug("change_endline_speed method called")
		endline_style = self.combo_endline_params.currentText()
		logging.debug(endline_style)
		# FIND A MORE ELEGANT AND PYTHONIC WAY TO DO THIS.
		if(endline_style == ENDLINE_OPTIONS[0]):						# "No Line Adjust"
			self.endline = b""
		elif (endline_style == ENDLINE_OPTIONS[1]):						# "New Line"
			self.endline = b"\n"				
		elif (endline_style == ENDLINE_OPTIONS[2]):						# "Carriage Return"
			self.endline = b"\r"		
		elif (endline_style == ENDLINE_OPTIONS[3]):						# "Both NL & CR"
			self.endline = b"\r\n"	
			
		logging.debug(self.endline)			
		
	def on_button_connect_click(self):									# this button changes text to disconnect when a connection is succesful.
		logging.debug("Connect Button Clicked")									# how to determine a connection was succesful ???
		self.button_serial_connect.setEnabled(False)
		self.button_serial_disconnect.setEnabled(True)
		self.combo_serial_port.setEnabled(False)
		self.combo_serial_speed.setEnabled(False)
		self.combo_endline_params.setEnabled(False)
		self.textbox_send_command.setEnabled(True)
		self.button_pause.setEnabled(True)
		self.record_timer.start()
		self.plot_frame.dataset = self.dataset
		self.status_bar.showMessage("Connecting...")					# showing sth is happening. 
		self.plot_frame.enable_toggles("all")
		self.start_serial()
		self.setup_slave()												# depending on the choosen mode, there are some requirements to start getting data.
		self.on_button_play()
		
		self.first_toggles = 0


	def serial_connect(self, port_name):
		logging.debug("serial_connect method called")
		logging.debug(port_name)
		logging.debug("port name " + port_name)

		try:															# closing port just in case was already open. (SHOULDN'T BE !!!)
			self.serial_port.close()
			logging.debug("Serial port closed")	
			logging.debug("IT SHOULD HAVE BEEN ALWAYS CLOSED, REVIEW CODE!!!")	# even though the port can't be closed, this message is shown. why ???
		except:
			logging.debug("serial port couldn't be closed")
			logging.debug("Wasn't open, as it should always be")


		try:															# try to establish serial connection 
			self.serial_port = serial.Serial(							# serial constructor
				port=port_name, 
				baudrate= self.serial_baudrate,		
				#baudrate = 115200,
				#bytesize=EIGHTBITS, 
				#parity=PARITY_NONE, 
				#stopbits=STOPBITS_ONE, 
				#timeout=None, 
				timeout=0,												# whenever there's no dat on the buffer, returns inmediately (spits '\0')
				xonxoff=False, 
				rtscts=False, 
				write_timeout=None, 
				dsrdtr=False, 
				inter_byte_timeout=None, 
				exclusive=None
				)
			
		except Exception as e:											# both port open, and somebody else blocking the port are IO errors.
			logging.debug("ERROR OPENING SERIAL PORT")
			self.on_port_error(e)
					
		except:
			logging.debug("UNKNOWN ERROR OPENING SERIAL PORT")

		else:															# IN CASE THERE'S NO EXCEPTION (I HOPE)
			logging.debug("SERIAL CONNECTION SUCCESFUL !")
			self.status_bar.showMessage("Connected")
			# here we should also add going  to the "DISCONNECT" state.
			
		logging.debug("serial_port.is_open:")
		logging.debug(self.serial_port.is_open)
		logging.debug("done: ")
		#logging.debug(self.done)			

	def start_serial(self):
		# first ensure connection is properly made
		self.serial_connect(self.serial_port_name)
		# 2. move status to connected 
		# 3. start the timer to collect the data
		self.serial_timer.start()

		# 4. Initialization stuff required by the remote serial device:
		self.init_emg_sensor()

	def init_emg_sensor(self):
		# initialization stuff (things required for the sensors to start sending shit)
		# message = "E=1;"														# enable EMG data.
		# self.serial_message_to_send = message.encode('utf-8')					# this should have effect on the serial_thread
		# logging.debug(self.serial_message_to_send)
		# self.serial_port.write(self.serial_message_to_send)
		# message = "START;"
		# self.serial_message_to_send = message.encode('utf-8')					# this should have effect on the serial_thread
		# logging.debug(self.serial_message_to_send)
		# self.serial_port.write(self.serial_message_to_send)
		pass

	def on_button_disconnect_click(self):
		print("Disconnect Button Clicked")
		self.button_serial_disconnect.setEnabled(False)					# toggle the enable of the connect/disconnect buttons
		self.button_serial_connect.setEnabled(True)
		self.combo_serial_port.setEnabled(True)
		self.combo_serial_speed.setEnabled(True)
		self.combo_endline_params.setEnabled(True)
		self.textbox_send_command.setEnabled(False)
		self.status_bar.showMessage("Disconnected")						# showing sth is happening. 
		self.plot_frame.clear_plot()									# clear plot
		self.clear_dataset()
		self.plot_frame.dataset = self.dataset  						# when clearing the dataset, we need to reassign the plot frame !!! --> this is not right!!!, but works.
		print("self.plot_frame.dataset")
		print(self.plot_frame.dataset)
		self.plot_frame.clear_channels_labels()
		self.plot_frame.check_toggles("none")
		self.plot_frame.enable_toggles("none")
		self.serial_port.close()
		self.serial_timer.stop()
		self.plot_frame.plot_timer.stop()
		self.on_record_timer()											# this should save what's left to the file and clear the dataset
		self.on_button_stop()											# and this should disable the recording, if we disconnect the serial port
		self.record_timer.stop()
		print(SEPARATOR)


	def on_button_pause(self):
		# pause the plot:
		# so stop the update timer. #
		print("on_button_pause method: ")
		#self.plot_frame.plot_timer.stop()								# but we won't be able to rearm...
		self.plot_frame.stop_plotting()
		self.button_pause.setEnabled(False)
		self.button_play.setEnabled(True)
		
	def on_button_play(self):
		# pause the plot:
		# so stop the update timer. #
		print("on_button_play method: ")
		self.button_play.setEnabled(False)
		self.button_pause.setEnabled(True)
		#self.plot_frame.plot_timer.start()								# but we won't be able to rearm...
		self.plot_frame.start_plotting()

	def on_button_record(self):
		print("on_button_record method: ")
		self.start_recording()
		self.set_logfile()
		self.button_record.setEnabled(False)
		self.button_stop.setEnabled(True)

	def on_button_stop(self):
		print("on_button_stop method: ")
		self.stop_recording()				
		#self.log_file.close()
		self.button_stop.setEnabled(False)
		self.button_record.setEnabled(True)
	
	def on_button_autoscale(self, i = 1):
		
		#if (i == 0):
		#	self.button_autoscale.setChecked(False)
		#elif ( i ==1): 
		#	self.button_autoscale.setChecked(True)

		#if (in == 1):
		#if self.button_autoscale.isChecked():							# if checked, we uncheck and disable autoscale.
			print("Autorange enabled")
			self.plot_frame.graph.enableAutoRange(axis='y')
			self.plot_frame.graph.setAutoVisible(y=True)				# don't know what's this
			#self.button_autoscale.setChecked(True)
			#self.plot_frame.max_value[0] = 0
			#self.plot_frame.max_value[1] = 0
			#self.plot_frame.min_value[0] = 0
			#self.plot_frame.min_value[1] = 0
			val = 'NaN'
			for index in range(0,8):
				self.plot_frame.label_cursor[index].setText(val)

			i = 0

		#elif(i == 0):
		#	print("Autorange disabled")
		#	self.button_autoscale.setEnabled(True)
			#self.button_autoscale.setChecked(False)
		#	i = 1

					
	def on_port_select(self,port_name):									# callback when COM port is selected at the menu.
		#1. get the selected port name via the text. 
		#2. delete the old list, and regenerate it, so when we push again the com port list is updated.
		#3. create a thread for whatever related with the serial communication, and start running it.
		#. open a serial communication. --> this belongs to the thread. 
		
		# START THE THREAD WHICH WILL BE IN CHARGE OF RECEIVING THE SERIAL DATA #
		#self.serial_connect(port_name)
		logging.debug("Method on_port_select called	")
		self.serial_port_name = port_name
		logging.debug(self.serial_port_name)

	def on_arrow_up(self):
		print("on_arrow_up method called")
		# change y axis from plot
		y_axis = self.plot_frame.graph.getAxis('left').range
		print(y_axis)
		for i in range(len(y_axis)):
			y_axis[i] = y_axis[i]/2
		self.plot_frame.graph.setRange(yRange = y_axis)
		
	def on_arrow_down(self):
		print("on_arrow_down method called")		
		# change y axis from plot
		y_axis = self.plot_frame.graph.getAxis('left').range
		print(y_axis)
		for i in range(len(y_axis)):
			y_axis[i] = y_axis[i]*2
		self.plot_frame.graph.setRange(yRange = y_axis)		
	
	def on_arrow_left(self):
		print("on_arrow_left method called")
		x_axis = self.plot_frame.graph.getAxis('bottom').range
		print(x_axis)
		for i in range(len(x_axis)):
			x_axis[i] = x_axis[i]/2
		self.plot_frame.graph.setRange(xRange = x_axis)			

	def on_arrow_right(self):
		print("on_arrow_right method called")
		x_axis = self.plot_frame.graph.getAxis('bottom').range
		print(x_axis)
		for i in range(len(x_axis)):
			x_axis[i] = x_axis[i]*2
		self.plot_frame.graph.setRange(xRange = x_axis)	

	def start_recording(self):
		self.set_logfile()
		self.recording = True
		
	def stop_recording(self):
		self.recording = False

	def on_record_timer(self):
		#print("on_record_timer method called:")
		t0 = time.time()
		
			# ~ print("self.dataset")
			# ~ for line in self.dataset:
				# ~ print(line)
		
		if(self.recording == True):
			print("saving data to file")
			# ~ np_data = np.array(self.dataset)
			# ~ np_data_t = np_data.transpose()
			# ~ print("Data")
			# ~ print(np_data)
			# ~ print(SEPARATOR)
			# ~ print("Transposed data")
			# ~ print(np_data_t)
			# ~ print(SEPARATOR)
			with open(self.log_full_path, mode = 'a', newline = '') as csv_file:	# "log_file.csv" if will probably smash the data after first write!!!
				dataset_writer = csv.writer(csv_file, delimiter = ',')				# standard way to write to csv file
				for value in self.dataset[0:self.n_data_points]:						# only record the first "POINT_PER_PLOT" data points.
					dataset_writer.writerow(value)
		
		t = time.time()
		dt = t-t0
		# print(dt)
		# print(SEPARATOR)
		#
		# print("dataset lenght[0] on_record_timer():")
		# print(len(self.dataset))										# we need to use the first item, as dataset will have a lenght depending on the number of plots received from Microcontroller.
		# print("dataset lenght on_timer")
		
			
		while(len(self.dataset) > 3*self.n_data_points):					# this ensures there's always enough data to plot the whole window.
			logging.debug("Dataset removing some points")
			# ~ for i in range(self.n_data_points-1):
				# ~ self.dataset.pop()
			logging.debug(len(self.dataset))
			self.dataset = self.dataset[self.n_data_points:]				# removes the first "self.n_data_points" values from the dataset.
			logging.debug(len(self.dataset))
			self.plot_frame.dataset = self.dataset
			#self.clear_dataset()	# doesn't make any difference
			self.plot_frame.dataset_changed = True						# if we remove a part of the dataset, it is indeed changing. 
			logging.debug("dataset_length after removing some points")
			logging.debug(len(self.dataset))

	def on_serial_timer(self):
		if(self.parsing_style == "Microcontroller"):
			self.add_Microcontroller_data()
		elif(self.parsing_style == "emg"):
			self.add_emg_sensor_data()
		elif(self.parsing_style == "emg_new"):
			self.add_emg_new_sensor_data()

	def setup_slave(self):						# READ/WRITE CONFIG this method performs all the tasks required to write and request data to/from slave
		print("setting up slave device")
		# depending on the parsing style, we identify different remote devices and data formats #
		if(self.parsing_style == "Microcontroller"):	# just writes the ASCII formated data, usually associted with the TEENSY device, or for any other GENERIC device (compatible with Microcontroller plotter)
			pass								# no configuration to be done here (at least for now)
		elif(self.parsing_style == "emg"):
			# #self.send_serial("N?")				# this command requests number of sensors in the remote device
			# self.send_serial("E=1")			# ENABLES EMG data
			# self.send_serial("START")			# STARTS COLLECTING EMG data
			pass
		elif(self.parsing_style == "emg_new"):
			print("configuring the emg_new device")
			print("reading the number of sensors")
			self.send_serial("N?")
			n_sensors = self.serial_port.readline()
			print(n_sensors)
			# for i in range(1,100):
			# 	n_sensors = self.serial_port.read(500)
			# 	print(n_sensors)


			# UNCOMMENT THESE TWO LINES WHEN FINISHED DEBUGGING !!!#
			self.send_serial("E=1")  # ENABLES EMG data
			self.send_serial("START")  # STARTS COLLECTING EMG data
			pass

		# read variable nSensors

	def add_Microcontroller_data(self):

		byte_buffer = ''
		mid_buffer = ''

		try:
			byte_buffer = self.serial_port.read(SERIAL_BUFFER_SIZE)		# up to 1000 or as much as in buffer.
		except Exception as e:
			self.on_port_error(e)
			self.on_button_disconnect_click()							# we've crashed the serial, so disconnect and REFRESH PORTS!!!
		else:															# if except doens't happen
			try:
				mid_buffer = byte_buffer.decode('utf-8')				# SHOULDN'T THIS BE PARSING ALREADY???
				#print(mid_buffer)
			except Exception as e:
				print(SEPARATOR)
				# print(e)
				self.on_port_error(e)
			else:
				self.read_buffer = self.read_buffer + mid_buffer
				#print(self.read_buffer)
				data_points = self.read_buffer.split(self.endline)
				#print(data_points)
				self.read_buffer = data_points[-1]  # clean the buffer, saving the non completed data_points
				a = data_points[:-1]
				for data_point in a:  # so all data points except last.
					#print(data_point)
					self.Microcontroller_parse(data_point)

	def Microcontroller_parse(self,readed):									# perform data processing as required (START WITH Microcontroller STYLE, AND ADD OTHER STYLES).#

		vals = readed.replace(' ',',')									# replace empty spaces for commas.
		#print(vals)
		vals = vals.replace(':',',')				# fast fix for inline labels incompatibility. MAKE IT BETTER !!!
		#print(vals)
		vals = vals.split(',')											# Microcontroller serial plotter splits with both characters.
		#print(vals[0])

		valsf = []

		self.plot_frame.n_plots = 5

		if(vals[0] == ''):
			self.timeouts = self.timeouts + 1
			print("Timeout")
			print("Total number of timeouts: "+ str(self.timeouts))
		else:
			text_vals = []
			for val in vals:
				try:

					valsf.append(float(val))
					
				except:
					# logging.debug("It contains also text")
					# add to a captions vector
					text_vals.append(val)
					char_strings = [x.strip('\x00') for x in text_vals]
					char_list = [x for x in char_strings if x != '']
					#print(char_list)
					self.plot_frame.set_channels_labels(char_list)
				else:
					self.add_values_to_dataset(valsf)

			for i in range(my_graph.MAX_PLOTS):

				try:
					valsf[i] *= K 	#ADC value convert to voltage
				except:
					pass
				
				try:					
					if i == 0:	
						valsf[i] = valsf[i] + self.plot_frame.slider1_value #change position of graphs of functions (slider)
						valsf[i] *= self.plot_frame.dial1_value #change scale [div/V] of graphs of functions (dial)
					elif i == 1:
						valsf[i] += self.plot_frame.slider2_value
						valsf[i] *= self.plot_frame.dial2_value
					#print(valsf[0])										
				except:
					pass

				try:
					if i == 0 or 1:
						if valsf[i] > self.maxsimum[i]:
							self.maxsimum[i] = valsf[i]
							self.plot_frame.max_value[i] = self.maxsimum[i]
					if i == 0 or 1:
						if valsf[i] < self.minimum[i]:
							self.minimum[i] = valsf[i]
							self.plot_frame.min_value[i] = self.minimum[i]
				except:
					pass
				
				#To Do FFT HERE
				'''
				try:
					if self.plot_frame.FFT.isChecked():
						print("FFT to Do")
						

						if i == 0: # or 1:						
							# Wątek zbierania danych
							#data_thread = threading.Thread(target=self.collect_data(valsf[i]))
							#data_thread.daemon = True
							#data_thread.start()
							#print("elo")

							# Oczekiwanie na zakończenie zbierania danych
							#data_thread.join()

							# Obliczanie FFT

							#print(valsf[i])
							x0_data = self.collect_data(valsf[i])
							#print(x0_data)
							Y0_data, freq0_data = self.compute_fft(x0_data)
							#print(Y0_data)
							valsf[i] = np.abs(Y_data[:n // 2])
							# Wykres FFT
							plt.figure(figsize=(8, 6))
							plt.plot(freq_data0, np.abs(Y0_data[:n // 2]), 'r', linestyle='-', marker='o')
							plt.xlabel('Częstotliwość (Hz)')
							plt.ylabel('|Y(freq)|')
							plt.title('FFT sygnału z Arduino')
							plt.grid(True)
							plt.show() 
							#elif i == 1:
							#	x1_data = collect_data()
							#	Y1_data, freq1_data = compute_fft(x1_data)
							#	#valsf[i] = np.abs(Y_data[:n // 2])


							#self.FFT(valsf[i])
							#valsf[i] = np.fft.fft(valsf[i])
				except:
					pass
				'''

			self.plot_frame.update()
			#print("dataset_changed = "+ str(self.plot_frame.graph.dataset_changed))

	def collect_data(self, data):

		x = np.zeros(n)
		for i in range(n):
			x[i] = data
		return x

	def compute_fft(self, x):
		Y = np.fft.fft(x) / n
		freq = np.fft.fftfreq(n, d=Ts)
		freq = freq[:n // 2]  # Rozważ tylko częstotliwości dodatnie
		return Y, freq

	def add_values_to_dataset(self,values):
		for j in range(5):
			self.dataset.append(values)  # appends all channels together
		#print(self.dataset[0])
		# enabling corresponding toggles #
		for i in range(my_graph.MAX_PLOTS):  # this may not be the greatest option. it's fine.
			try:
				a = values[i]  # should crash after 4th element CHEAP FIX, MAKE IT BETTER !!!
				# self.dataset[i].append(valsf[i])				# if valsf has only 4 elements, it will throw error at 5th
				self.plot_frame.toggles[i].setEnabled(True)  # enable all graphs conataining data

				if (
					self.first_toggles <= 2):  # THIS SHOULD BE IF NO DATA ON DATASET[I], OR ONLY ONE ELEMENT ON DATASET[I]
					self.plot_frame.toggles[i].setChecked(True)
			except:
				pass

		self.first_toggles = self.first_toggles + 1				# ???

	def FFT(self, vals):
		#fft_result = np.fft.fft(vals)
		print("Elo")

	def add_emg_sensor_data(self):								# reads the data in the specific binary format of the emg sensor

		byte_buffer = []
		num_buffer = []

		try:
			byte_buffer = self.serial_port.read(SERIAL_BUFFER_SIZE)		# up to 1000 or as much as in buffer.
		except Exception as e:
			self.on_port_error(e)
			self.on_button_disconnect_click()							# we've crashed the serial, so disconnect and REFRESH PORTS!!!
		else:															# if except doens't happen
			# print("byte_buffer:")
			# print(byte_buffer)

			try:
				for byte in byte_buffer:
					num = int(byte)
					num_buffer.append(num)
					# print("num_buffer:")
					# print(num_buffer)
				# here we will have a buffer with lots of numbers (32,45,33,0,45,54,33,0,32...)
			except Exception as e:
				print("ERROR: -------------------------")
				print(e)
				print(SEPARATOR)
				self.on_port_error(e)
			else:
				self.read_buffer = self.read_buffer + num_buffer			# read buffer contains what was left from previous iteration
				data_points = self.split_number_array(self.read_buffer,0)	# we split the buffer on 'number 0' received (end of data_points)
				self.read_buffer = data_points[-1]  						# clean the buffer, saving the non completed data_points
				a = data_points[:-1]										# get all the completed ones
				for data_point in a:  										# so all data points except last.
					if len(data_point) == 4:								# FIX THIS!: we expect 4 data values per data point, if not, it means corrupted data.
						self.add_values_to_dataset(data_point)

				# HERE IS WHERE WE GET THE PROBLEMATIC DATA POINTS, SO THE RIGHT PLACE TO FIX IF THERE AREN'T ENOUGH POINTS.
					else:
						for i in range(int(len(data_point)/4)+1):
							self.add_values_to_dataset([0,0,0,0])				# this indicates error code, data isn't having the 4 expected values




				pass
		self.plot_frame.update()
		# num = True
		# vals = []
		# while(num != 0):
		# 	byte = self.serial_port.read()
		# 	num = int.from_bytes(byte, byteorder='big', signed=False)  # decoding to store in file
		# 	num = float(num)
		# 	vals.append(num)
		# vals = vals[:-1]										# remove the final zero
		# if(len(vals) > 1):										# bad trick to remove zero data value array !!!
		# 	self.add_values_to_dataset(vals)
		# 	self.plot_frame.update()
		# 	#return(vals)
	def add_emg_new_sensor_data(self):								# reads the data in the specific binary format of the emg sensor
		#print("add_emg_new_sensor_data")
		byte_buffer = []
		num_buffer = []

		try:
			byte_buffer = self.serial_port.read(SERIAL_BUFFER_SIZE)		# up to 1000 or as much as in buffer.
		except Exception as e:
			self.on_port_error(e)
			self.on_button_disconnect_click()							# we've crashed the serial, so disconnect and REFRESH PORTS!!!
		else:															# if except doens't happen
			# print("byte_buffer:")
			# print(byte_buffer)

			try:
				for byte in byte_buffer:
					num = int(byte)
					num_buffer.append(num)
				# print("num_buffer:")
				# print(num_buffer)
				# here we will have a buffer with lots of numbers (32,45,33,0,45,54,33,0,32...)
			except Exception as e:
				print("ERROR: -------------------------")
				print(e)
				print(SEPARATOR)
				self.on_port_error(e)
			else:
				self.read_buffer = self.read_buffer + num_buffer				# read buffer contains what was left from previous iteration
				data_points = self.split_number_array(self.read_buffer,0xFF)	# we split the buffer on 'number FF' received (end of data_points)
				self.read_buffer = data_points[-1]  							# clean the buffer, saving the non completed data_points
				a = data_points[:-1]											# get all the completed ones
				for data_point in a:  											# so all data points except last.
					if len(data_point) == 4:									# FIX THIS!: we expect 4 data values per data point, if not, it means corrupted data.
						self.add_values_to_dataset(data_point)
						pass
				# HERE IS WHERE WE GET THE PROBLEMATIC DATA POINTS, SO THE RIGHT PLACE TO FIX IF THERE AREN'T ENOUGH POINTS.
					else:
						for i in range(int(len(data_point)/4)+1):
							self.add_values_to_dataset([0,0,0,0])				# this indicates error code, data isn't having the 4 expected values

		self.plot_frame.update()

	def split_number_array(self, array, separator):
		results = []
		res = []
		for val in array:
			# print(res)
			# print(val)
			if val is not separator:
				res.append(val)
			else:
				results.append(res)
				res = []
		results.append(res)  # what's left on the res after the separator

		return(results)

	def emg_parse(self):
		pass

		#num = int.from_bytes(byte, byteorder='big', signed=False)  # decoding to store in file

	def init_dataset(self):
		self.dataset = []

	def clear_dataset(self):	
		# initializing empty dataset #
		self.dataset = []

	def on_port_error(self,e):											# triggered by the serial thread, shows a window saying port is used by sb else.

		desc = str(e)
		logging.debug(type(e))
		logging.debug(desc)
		error_type = None
		i = desc.find("Port is already open.")
		if(i != -1):
			print("PORT ALREADY OPEN BY THIS APPLICATION")
			error_type = 1
			logging.debug(i)	
		i = desc.find("FileNotFoundError")
		if(i != -1):
			logging.debug("DEVICE IS NOT CONNECTED, EVEN THOUGH PORT IS LISTED")
			error_type = 2										# 
		i = desc.find("PermissionError")
		if(i != -1):
			logging.debug("SOMEONE ELSE HAS OPEN THE PORT")
			error_type = 3									# shows dialog the por is used (better mw or thread?) --> MW, IT'S GUI.
		
		i = desc.find("OSError")
		if(i != -1):
			logging.debug("BLUETOOTH DEVICE NOT REACHABLE ?")	
			error_type = 4
			
		i = desc.find("ClearCommError")
		if(i != -1):
			logging.debug("DEVICE CABLE UNGRACEFULLY DISCONNECTED")	
			error_type = 5



		# ~ i = desc.find("'utf-8' codec can't decode byte")			# NOT WORKING !!! (GIVING MORE ISSUES THAN IT SOLVED)
		# ~ if(i != -1):
			# ~ logging.debug("WRONG SERIAL BAUDRATE?")	
			# ~ error_type = 6

		self.error_type = error_type
		
		# ~ logging.debug("Error on serial port opening detected: ")
		# ~ logging.debug(self.error_type)
		self.handle_errors_flag = True									# more global variables to fuck things up even more. 
		self.handle_port_errors()
		
	def handle_port_errors(self):										# made a trick, port_errors is a class variable (yup, dirty as fuck !!!)
		
		if(self.error_type == 1):										# this means already open, should never happen.
			logging.warning("ERROR TYPE 1")										
			d = QMessageBox.critical(
				self,
				"Serial port Blocked",
				"The serial port selected is in use by other application",
				buttons=QMessageBox.Ok
			)		
		if(self.error_type == 2):										# this means device not connected
			logging.warning("ERROR TYPE 2")
			d = QMessageBox.critical(
				self,
				"Serial Device is not connected",
				"Device not connected.\n Please check your cables/connections.  ",
				buttons=QMessageBox.Ok
			)		
		if(self.error_type == 3):										# this means locked by sb else. 
			d = QMessageBox.critical(
				self,
				"Serial port Blocked",
				"The serial port selected is in use by other application.  ",
				buttons=QMessageBox.Ok
			)

			self.on_button_disconnect_click()							# resetting to the default "waiting for connect" situation
			self.handle_errors_flag = False		
		if(self.error_type == 4):										# this means device not connected
			logging.warning("ERROR TYPE 4")
			d = QMessageBox.critical(
				self,
				"Serial Device Unreachable",
				"Serial device couldn't be reached,\n Bluetooth device too far? ",
				buttons=QMessageBox.Ok
			)
		if(self.error_type == 5):										# this means device not connected
			logging.warning("ERROR TYPE 5")
			d = QMessageBox.critical(
				self,
				"Serial Cable disconnected while transmitting",
				"Serial device was ungracefully disconnected, please check the cables",
				buttons=QMessageBox.Ok
			)
		if(self.error_type == 6):										# this means device not connected
			logging.warning("ERROR TYPE 6")
			d = QMessageBox.critical(
				self,
				"Serial wrong decoding",
				"There are problems decoding the data\n probably due to a wrong baudrate.",
				buttons=QMessageBox.Ok
			)
		self.on_button_disconnect_click()							# resetting to the default "waiting for connect" situation
		self.handle_errors_flag = False				
		self.error_type = None											# cleaning unhnandled errors flags. 

	# check all themes and use lambda functions may be an option to use more themes #
	def set_dark_theme(self):
		self.palette = pyqt_custom_palettes.dark_palette()
		self.setPalette(self.palette)
		self.plot_frame.setBackground([60,60,60])
		
	def set_light_theme(self):
		self.palette = pyqt_custom_palettes.light_palette()
		self.setPalette(self.palette)
		self.plot_frame.setBackground([220,220,220])

	def set_re_theme(self):
		self.palette = pyqt_custom_palettes.re_palette()
		self.setPalette(self.palette)

	def set_Microcontroller_parsing(self):
		self.read_buffer = ""
		self.parsing_style = "Microcontroller"

	def set_emg_parsing(self):
		self.read_buffer = []
		self.parsing_style = "emg"

	def set_emg_parsing_new(self):
		self.read_buffer = []
		self.parsing_style = "emg_new"

	def set_plot_range(self):
		logging.debug("set_range_action method called")
		plot_range_dialog = RangeDialog()

		if plot_range_dialog.exec_():
			print(plot_range_dialog.getInputs())
			self.plot_frame.graph.setLimits(yMin=int(plot_range_dialog.getInputs()[0]),
											yMax=int(plot_range_dialog.getInputs()[1]))

	def set_n_plot_points(self):
		print("set_n_plot_points method called")
		i, okPressed = QInputDialog.getText(self, "Set n points", "Number of plot points (recommended max. 5000):")
		if okPressed:
			self.n_data_points = int(i)
			self.plot_frame.set_max_points(self.n_data_points)

	def update_serial_ports(self):										# we update the list every time we go over the list of serial ports.
		# here we need to add an entry for each serial port avaiable at the computer
		# 1. How to get the list of available serial ports ?
		
		self.serial_port_menu.clear()									# deletes all old actions on serial port menu	
		self.combo_serial_port.clear()
	
		
		self.get_serial_ports()											# meeded to list the serial ports at the menu
		# 3. How to ensure which serial ports are available ? (grey out the unusable ones)
		# 4. How to display properly each available serial port at the menu ?
		logging.debug (self.serial_ports)
		if self.serial_ports != []:
			for port in self.serial_ports:
				port_name = port[0]
				logging.debug(port_name)
				b = self.serial_port_menu.addAction(port_name)
				# WE WON'T TRIGGER THE CONNECTION FROM THE BUTTON PUSH ANYMORE. 
				b.triggered.connect((lambda serial_connect, port_name=port_name: self.on_port_select(port_name)))				# just need to add somehow the serial port name here, and we're done.

				# here we need to add the connect method to the action click, and its result
				
			for port in self.serial_ports:								# same as adding all ports to action menu, but now using combo box. 
				port_name = port[0]	
				item = self.combo_serial_port.addItem(port_name)		# add new items 
				
				#b.currentTextChanged.connect((lambda serial_connect, port_name=port_name: self.on_port_select(port_name)))
		
		else:
				self.noserials = self.serial_port_menu.addAction("No serial Ports detected")
				self.noserials.setDisabled(True)

	def full_screen(self):												# it should be able to be detected from window class !!!
		if self.full_screen_flag == False:								
			self.showFullScreen()
			self.full_screen_flag = True
			logging.debug("Full Screen ENABLED")
		else:
			self.showNormal()
			self.full_screen_flag = False
			logging.debug("Full Screen DISABLED")
	
	# KEYPRESS HANDLER FOR SHORTCUTS ####
	def keyPressEvent(self, event):
		if not event.isAutoRepeat():
			print(event.text())	
			# FULL SHORTCUT LIST #	
			# arrows#
			if event.key() == Qt.Key_Up:
				self.on_arrow_up()
			elif event.key() == Qt.Key_Down:
				self.on_arrow_down()	
			elif event.key() == Qt.Key_Left:
				self.on_arrow_left()
			elif event.key() == Qt.Key_Right:
				self.on_arrow_right()
			#letters#
			elif event.text() == 'f':
				self.full_screen()
			elif event.text() == 'c':
				self.on_button_connect_click()
			elif event.text() == 'd':
				self.on_button_disconnect_click()
			elif event.text() == 'u':
				self.update_serial_ports()
			elif event.text() == 'p':
				self.on_button_pause()
			elif event.text() == 'y':
				self.on_button_play()
			elif event.text() == 'r':
				self.on_button_record()	
			elif event.text() == 's':
				self.on_button_autoscale()
			# numbers # 
			elif event.text() == 'º':
				print("enable all")
				self.plot_frame.check_toggles("all")					# this can't be done 
			elif event.text() == '0':									# toggles plots all/none
				self.plot_frame.check_toggles("none")


										
if __name__ == '__main__':
		
	app = QApplication(sys.argv)
	app.setStyle("Fusion")													# required to use it here
	mw = MainWindow()
	app.exec_()
