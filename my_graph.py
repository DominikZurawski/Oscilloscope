
import random
import time 
import logging
import math

import numpy as np


from PyQt5.QtWidgets import(
	QApplication,
	QMainWindow,
	QWidget,
	QHBoxLayout,																# create a new widget, which contains the MyGraph window
	QVBoxLayout, QGridLayout,QFormLayout ,
	QLabel, QPushButton, QGraphicsLineItem,
	QTabWidget, QLineEdit, QDateEdit,QPushButton, QCheckBox, QSlider, QDial, QSpinBox,
	QProxyStyle
)
from PyQt5.QtCore import Qt
from PyQt5.QtCore import(
	QTimer
)
import pyqtgraph as pg
import pyqtgraph.parametertree as ptree
import qtwidgets
from labelled_animated_toggle import *

COLORS = ["#ff0000","#00ff00","#0000ff","#ffff00","#ff00ff","#00ffff",
			"#FFA500","#7fff00","#00ff7f","#007FFF","#EE82EE","#FF007F",
			"#ff0000","#00ff00","#0000ff","#ffff00","#ff00ff","#00ffff",
			"#FFA500","#7fff00","#00ff7f","#007FFF","#EE82EE","#FF007F",]

MAX_PLOTS = 4															# Absolute maximum number of plots, change if needed !!
ABS_Y_MAX = 1000000														# Absolute maximum Y range, is fixed, and can only be changed on compilation time.
DEFAULT_Y_MAX = 100000
DEFAULT_Y_MIN = -100000
DEFAULT_MAX_POINTS = 2000
CHANNEL_LABEL_MAX_LEN = 10
		
class MyPlot(QWidget):
					
	n_plots = 12														# number of plots on the current plot. 
	plot_tick_ms = 50													# every "plot_tick_ms", the plot updates, no matter if there's new data or not.
	dataset = []														# complete dataset, this should go to a file.							
	toggles = []															# references to the toggles which enable/disable plots.													
	checkboxes = []
	sliders = []
	dial = []
	spin_box = []
	Btns = []
	label_cursor = []

	def __init__(self, dataset = [], max_points = DEFAULT_MAX_POINTS):
		super().__init__()
		#super().__init__()	

		self.slider1_value = 0
		self.slider2_value = 0
		self.dial1_value = 1
		self.dial2_value = 1

		# central widget #
		self.layout = QHBoxLayout()										# that's how we will lay out the window
		self.graph = MyGraph(dataset = dataset, max_points = max_points)
		self.settings = QWidget(self)
		self.settings.layout = QVBoxLayout()
		self.settings.setLayout(self.settings.layout)
		self.layout.addWidget(self.graph)
		self.layout.addWidget(self.settings)
		self.layout.setStretch(0, 4)  
		self.layout.setStretch(1, 1)
		self.setLayout(self.layout)

		self.plot_timer2 = QTimer()								
		self.plot_timer2.timeout.connect(self.update_label_cursor)
		self.plot_timer2.start(80)

		self.max_value = [None,None]
		self.min_value = [None,None]
		

		#Setting
		'''self.children=[
			dict(name='Channels', title='Channels', type='group'
				)]
		
		self.params = ptree.Parameter.create(name='Settings', type='group', children=self.children)
		self.pt = ptree.ParameterTree(showHeader=False)
		self.pt.setParameters(self.params)
		self.layout.addWidget(self.pt)
		self.params.child('Channels').sigValueChanged.connect(self.layout_channel_select)
		
		self.tabs = QTabWidget(self)

		self.settings = QWidget(self)
		self.settings.layout = QFormLayout()
		self.settings.setLayout(self.settings.layout)
		self.settings.layout.addRow('First Name:', QLineEdit(self))
		self.settings.layout.addRow('Last Name:', QLineEdit(self))
		self.settings.layout.addRow('DOB:', QDateEdit(self))

		
		# contact pane
		self.contact_page = QWidget(self)
		self.contact_page.layout = QVBoxLayout(self.contact_page)
		self.contact_page.setLayout(self.contact_page.layout)
		self.pushButton2 = QPushButton("Button in Tab 2")
		self.contact_page.layout.addWidget(self.pushButton2)
		'''
		self.layout_channel_select()
		self.layout_FFT_select()
		self.layout_slider_select()
		self.layout_dial_select()
		self.layout_cursor_select()

		# add pane to the tab widget
		#self.tabs.addTab(self.settings, 'Settings')
		#self.tabs.addTab(self.contact_page, 'Contact Info')

		#self.layout.addWidget(self.tabs)

	def layout_slider_select(self):
		self.layout_slider_select = QGridLayout()
		self.settings.layout.addLayout(self.layout_slider_select)
		self.slider_label = QLabel("Position:")
		self.layout_slider_select.addWidget(self.slider_label,0,1)
		self.add_slider()

	def add_slider(self):
		position = [(1,1), (1,2)]
		for i in range(0,2):	
			slider = QSlider(Qt.Vertical) 
			self.sliders.append(slider)
			slider.setRange(-50, 50)  # Set the range (from 0 to 100)
			slider.setValue(0)  # Set the initial value
			slider.setSingleStep(5)  # Set the step size
			slider.setPageStep(10)  # Set the page step
			slider.setMaximumHeight(100)
			slider.valueChanged.connect(self.get_slider_value)
			self.layout_slider_select.addWidget(slider, *position[i])

	def get_slider_value(self, value):
		sender = self.sender()
		self.slider_index = self.sliders.index(sender)
		slider = self.sliders[self.slider_index]
		#print(f"Slider {self.slider_index} value: {value}")

		if self.slider_index == 0:
			self.slider1_value = value
		elif self.slider_index == 1:
			self.slider2_value = value

	def layout_dial_select(self):
		self.layout_dial_select = QGridLayout()
		self.settings.layout.addLayout(self.layout_dial_select)
		dial_1_label = QLabel("X Range:")
		self.layout_dial_select.addWidget(dial_1_label,0,0)
		dial_2_label = QLabel("Y Range:")
		self.layout_dial_select.addWidget(dial_2_label,0,2)
		self.add_dial()

	def add_dial(self):
		position_1 = [(1,0), (1,2)]
		position_2 = [(2,0), (2,2)]
		for i in range(0,2):	
			dial = QDial()
			edit_box = QLineEdit()
			self.dial.append(dial)
			dial.setRange(1, 100)  # Set the range (from 0 to 100)
			dial.setValue(1)  # Set the initial value
			dial.setNotchesVisible(True)
			self.layout_dial_select.addWidget(dial, *position_1[i])
			dial.valueChanged.connect(self.get_dial_value)

			spin_box = QSpinBox()
			self.spin_box.append(spin_box)
			spin_box.setRange(1, 100)
			self.layout_dial_select.addWidget(spin_box, *position_2[i])
			spin_box.valueChanged.connect(self.update_spin_box)

	def update_spin_box(self, value):
		sender = self.sender()
		self.spin_index = self.spin_box.index(sender)
		spin_box = self.spin_box[self.spin_index]
		self.dial[self.spin_index].setValue(value)


	def get_dial_value(self, value):
		sender = self.sender()
		self.dial_index = self.dial.index(sender)
		dial = self.dial[self.dial_index]
		#print(f"Dial {index} value: {value}")

		self.spin_box[self.dial_index].setValue(value)

		if self.dial_index == 0:
			self.dial1_value = value
		elif self.dial_index == 1:
			self.dial2_value = value

	def layout_channel_select(self):
		self.layout_channel_select = QGridLayout()
		self.settings.layout.addLayout(self.layout_channel_select)
		self.channel_label = QLabel("Channels:")
		self.layout_channel_select.addWidget(self.channel_label,0,0)
		self.add_toggles()
				
		self.layout_channel_name = QHBoxLayout()
		# timer #


		self.plot_timer = QTimer()										# used to update the plot
		self.plot_timer.timeout.connect(self.on_plot_timer)

		self.start_plotting(self.plot_tick_ms)
		self.stop_plotting()	

		self.set_enabled_graphs("none")									# writes to a variable of graph indicating which graphs are on
		
		print("Init until set_enabled_graphs")		
		for toggle in self.toggles:
			toggle.setChecked(True)
			toggle.setEnabled(True)

	def layout_cursor_select(self):
		self.layout_cursor_select = QGridLayout()
		self.settings.layout.addLayout(self.layout_cursor_select)
		self.cursor_label = QLabel("Cursors:")
		self.layout_cursor_select.addWidget(self.cursor_label,0,0)
		#names = ['X1', 'X2', 'Y1', 'Y2']
		names = ['H', 'V']
		position = [(0,1), (0,2)] #, 
		pos = [(2,1), (2,2), (3,1), (3,2), (4,1), (4,2), (5,1), (5,2)]
		#self.add_checkBox(names, position)
		self.add_buttons(names, position)
		self.add_label(pos)

	def add_label(self, position):
		for i in range(0,len(position)):
			label_cursor = QLabel('0')
			self.label_cursor.append(label_cursor)
			#label_cursor.connect(self.update_label_cursor)
			self.layout_cursor_select.addWidget(label_cursor,*position[i])
			#self.plot_timer.timeout.connect(self.update_label_cursor)

	def update_label_cursor(self):
		for index in range(0,8):
			try:
				match index:
					case 0:
						try:
							x2, y2 = self.graph.cursor[index+2].getPos()
							x1, y1 = self.graph.cursor[index].getPos()
							value =  y2-y1 
							val = f"Δ {value:.3f}V"
							self.label_cursor[index].setText(val)
						except:
							pass
					case 1:
						try:
							x2, y2 = self.graph.cursor[index+2].getPos()
							x1, y1 = self.graph.cursor[index].getPos()
							value =  x2-x1 
							f = 1/value
							val = f"Δ {value:.3f}t   Δ{f:.3f}kHz"
							self.label_cursor[index].setText(val)
						except:
							pass
					case 2:

						val = f"CH1 Max: {self.max_value[0]:.2f} V"
						self.label_cursor[index].setText(val)
					case 3:

						val = f"CH2 Max: {self.max_value[1]:.2f} V"
						self.label_cursor[index].setText(val)
					case 4:
						val = f"CH1 Min: {self.min_value[0]:.2f} V"
						self.label_cursor[index].setText(val)
					case 5:
						val = f"CH2 Min: {self.min_value[1]:.2f} V"
						self.label_cursor[index].setText(val)
					case 6:
						value = (self.max_value[0] + self.min_value[0])/2
						val = f"Avg CH1: {value:.2f} V"
						self.label_cursor[index].setText(val)
					case 7:
						value = (self.max_value[0] + self.min_value[1])/2
						val = f"Avg CH2: {value:.2f} V"
						self.label_cursor[index].setText(val)
			except:
				pass

	def layout_FFT_select(self):
		self.layout_FFT_select = QGridLayout()
		self.settings.layout.addLayout(self.layout_FFT_select)
		self.add_FFT_button()

	def add_FFT_button(self):
			FFT = QPushButton(text='FFT')
			self.FFT = FFT
			FFT.setCheckable(True)
			FFT.setFixedSize(100, 30)
			FFT.clicked.connect(self.FFT_action)
			self.layout_FFT_select.addWidget(FFT)

	def FFT_action(self):
		sender = self.sender()
		if sender.isChecked():
			sender.setStyleSheet("background-color: blue; color: white;")
			#...Akcja FFT
		else:
			sender.setStyleSheet("background-color: #333333; color: white;")
		

	def add_buttons(self, names, position):
		for i in range(0,len(names)):
			Btn = QPushButton(text=names[i])
			self.Btns.append(Btn)
			Btn.setCheckable(True)
			Btn.setFixedSize(100, 30)
			Btn.clicked.connect(self.Btn_action)
			self.layout_cursor_select.addWidget(Btn,*position[i])

	def Btn_action(self):
		sender = self.sender()
		index = self.Btns.index(sender)

		if sender.isChecked():
			sender.setStyleSheet("background-color: blue; color: white;")
			self.graph.create_cursor(index)

		else: 
			sender.setStyleSheet("background-color: #333333; color: white;")
			self.graph.removeItem(self.graph.cursor[index])
			self.graph.removeItem(self.graph.cursor[index+2])
			self.graph.cursor[index] = None


	'''
	def add_checkBox(self, names, position):		
		for i in range(0,len(names)):
			checkbox = QCheckBox(names[i], self)
			self.checkboxes.append(checkbox)
			checkbox.setChecked(False)  # Set the initial state (checked)
			checkbox.setTristate(False) 
			checkbox.stateChanged.connect(self.handle_checkbox_change)
			self.layout_cursor_select.addWidget(checkbox,*position[i])


	def handle_checkbox_change(self, state):
		# Find which checkbox sent the signal
		sender = self.sender()
		index = self.checkboxes.index(sender) + 1

		if state == 2:  
			self.graph.create_cursor(index-1)
		else: 
			self.graph.removeItem(self.graph.cursor[index-1])
			self.graph.cursor[index-1] = None
	'''

	def add_toggles(self):												# encapsulates the creation of the toggles, and their initial setup.
		for i in range(0, MAX_PLOTS):
			position = [(0,1), (0,2), (2,1), (2,2)]
			color = COLORS[i]
			label_toggle = LabelledAnimatedToggle(color = color)
			self.toggles.append(label_toggle)
			label_toggle.setChecked(False)						# all toggles not checked by default	# create new method to call the toggle method?
			label_toggle.setEnabled(True)						# all toggles not enabled by default
			if i<2:
				self.layout_channel_select.addWidget(label_toggle, *position[i])
			
	def enable_toggles(self,val):
		if(val == "all"):
			for i in range(MAX_PLOTS):
				self.toggles[i].setEnabled(True)
		elif(val == "none"):
			for i in range(MAX_PLOTS):
				#print(i)
				self.toggles[i].setEnabled(False) 
		else:
			pass			# fill with behavior if val is a vector
		
	def check_toggles(self,vals):
		if(vals == "all"):
			for i in range(MAX_PLOTS):
				if(self.toggles[i].isEnabled()):						# so we can only check enabled toggles. 
					self.toggles[i].setChecked(True)
		elif(vals == "none"):
			for i in range(MAX_PLOTS):
				self.toggles[i].setChecked(False) 
		else:
			for i in range (MAX_PLOTS):
				self.toggles[i].setChecked(vals[i])						# vals should be a list with as many elements as toggles
		
	def set_channels_labels(self,names):								# each channel toggle has a label, set the text on that label.
		for i in range(MAX_PLOTS):										# we only assign the names of the plots that can be plotted
			try:
				name = names[i][:CHANNEL_LABEL_MAX_LEN]
				self.toggles[i].setLabel(name)
			except Exception as e:
				logging.debug("more channels than labels")
				
	def clear_channels_labels(self):									# clear all labels, usually to set them with new vals.
		for i in range(MAX_PLOTS):										# we only assign the names of the plots that can be plotted
			try:
				self.toggles[i].setLabel('')
			except Exception as e:
				logging.debug("more channels than labels")

	def set_max_points(self, max_points):
		self.graph.max_points = max_points
		self.graph.setLimits(xMin=0, xMax=self.graph.max_points)
		self.graph.setXRange(0,self.graph.max_points)



	def create_plots(self):
		self.graph.create_plots()

	def clear_plot(self):												# NOT WORKING 
		self.graph.clear_plot()

	def on_plot_timer(self):											# this is an option, to add together toggle processing and replot.
		enabled = []
		for i in range(0,MAX_PLOTS):
			if(self.toggles[i].toggle.isChecked()):
				enabled.append(True)
			else:
				enabled.append(False)	
				#print("off togle")	
			
		self.set_enabled_graphs(enabled)
		
		self.graph.dataset = self.dataset
						
		self.graph.on_plot_timer()										# calls the regular plot timer from graph.
		
	def plot_timer_start(self):											
		self.graph.timer.start()

	def update(self):													# notifies a change in the dataset
		self.graph.dataset_changed = True								# flag
		#self.graph.dataset = self.dataset
		
	def setBackground(self, color):
		self.graph.setBackground(color)

	def start_plotting(self, period = None):
		if(period == None):
			self.plot_timer.start()
		else:
			self.plot_timer.start(period)

	def stop_plotting(self):
		self.plot_timer.stop()

	def set_enabled_graphs(self, enable_list):
		if enable_list == "all":
			enable_list = []
			for i in range(MAX_PLOTS):
				enable_list.append(True)
		elif enable_list == "none":
			enable_list = []
			for i in range(MAX_PLOTS):
				enable_list.append(False)
		
		self.graph.set_enabled_graphs(enable_list)
						
class SliderProxyStyle(QProxyStyle):

	def pixelMetric(self, metric, option, widget):
		if metric == self.PM_SliderThickness:
			return 40  # Adjust the thickness as desired
		elif metric == self.PM_SliderLength:
			return 120  # Adjust the length as desired
		return super().pixelMetric(metric, option, widget)

    
        

class MyGraph(pg.PlotWidget):											# this is supposed to be the python convention for classes. 
	
	max_points = None													# maximum points per plot
	tvec = []															# independent variable, with "max_points" points.			
	n_plots = 12														# number of plots on the current plot. 
	first = True														# first iteration only creating the plots
	
	dataset = None														# complete dataset, this should go to a file.	
	np_dataset = None													# used for reverting the matrix.
	np_dataset_t = None						
	plot_refs = []														# references to the different added plots.
	plot_subset = []
	enabled_graphs = []													# enabled graphs ON GRAPH WINDOW, not on toggles. 
	cursor = []

	for i in range(0,MAX_PLOTS):
		enabled_graphs.append(False)									
													
	dataset_changed = False


	#dataset = np.array()
	
	def __init__(self, dataset = None, max_points = 80, title = "Oscilloscope"):

		
		for i in range(max_points):										# create a time vector --> move to NUMPY !!!
			self.tvec.append(i)
		
		self.dataset = dataset											# get the reference to the dataset given as input for the constructor
		self.max_points = max_points
			
		#self.plot_subset = self.dataset[:self.n_plots][-(self.max_points):]	 # get only the portion of the dataset which needs to be printed. 	
			
		super().__init__()		
		pg.setConfigOptions(antialias=False)																			# antialiasing for nicer view.
		#self.setBackground([70,70,70])	
		self.showGrid(x=True,y=True)																				# changing default background color.
		#self.showGrid(x = True, y = True, alpha = 0.5)
		self.setRange(xRange = [-self.max_points,self.max_points], yRange = [-8,10], padding=0) 	
		self.setLabels(left='Voltage [V]',bottom="t  [ms]")											# set default axes range
		self.setLimits(xMin=0, xMax=self.max_points, yMin=DEFAULT_Y_MIN, yMax=DEFAULT_Y_MAX)							# THIS MAY ENTER IN CONFIG WITH PLOTTING !!!
		#self.enableAutoRange(axis='x', enable=True)																	# enabling autorange for x axis
		legend = self.addLegend()
		self.setTitle(title)																				# if title is wanted
		self.cursor = [None, None, None, None]

	def create_plots(self):
		for i in range (MAX_PLOTS):
			logging.debug("val of i:" + str(i))
			p = self.plot(pen = (COLORS[i%24]))
			self.plot_refs.append(p)


	def clear_plot(self):												
		print("clear_plot method called")
		for i in range(len(self.plot_subset)):
			self.plot_refs[i].clear()									# clears the plot
			self.plot_refs[i].setData([0])								# sets the data to 0, may not be necessary
			#self.plot_subset[i] = []
			
	def set_enabled_graphs(self,enabled_graphs):						# enabled/dsables graphs ON GRAPH WINDOW, not on the toggles.
		self.enabled_graphs = enabled_graphs

	def create_cursor(self, index):
		i = index + 2

		if self.cursor[index]:
			self.removeItem(self.cursor[index])
			self.removeItem(self.cursor[i])

		match index:
			case 0:
				self.cursor[index] = pg.InfiniteLine(movable=True, angle=0, pen=(0, 0, 200),
					bounds = [-50, 50], hoverPen=(0,200,0), label='X'+str(i)+'={value:0.2f}V', 
					labelOpts={'color': (0,200,200), 'movable': True, 'fill': (0, 0, 200, 100)})
				self.cursor[i] = pg.InfiniteLine(movable=True, angle=0, pen=(0, 0, 200),
					bounds = [-50, 50], hoverPen=(0,200,0), label='X'+str(i+1)+'={value:0.2f}V', 
					labelOpts={'color': (0,200,200), 'movable': True, 'fill': (0, 0, 200, 100)})
				self.cursor[index].setPos([index, index])
				self.cursor[i].setPos([3.3, 3.3])
				self.addItem(self.cursor[index])
				self.addItem(self.cursor[i])

			case 1:
				self.cursor[index] = pg.InfiniteLine(movable=True, angle=90, label='Y'+str(index)+'={value:0.2f}ms', 
					labelOpts={'position':0.1, 'color': (200,200,100), 'fill': (200,200,200,50), 'movable': True})
				self.cursor[i] = pg.InfiniteLine(movable=True, angle=90, label='Y'+str(index+1)+'={value:0.2f}ms', 
					labelOpts={'position':0.1, 'color': (200,200,100), 'fill': (200,200,200,50), 'movable': True})
				self.cursor[index].setPos([index+10, index])
				self.cursor[i].setPos([i+10, i])
				self.addItem(self.cursor[index])
				self.addItem(self.cursor[i])


		'''
		match index:
			case 0 | 1:				
				self.cursor[index] = pg.InfiniteLine(movable=True, angle=0, pen=(0, 0, 200),
					bounds = [-50, 50], hoverPen=(0,200,0), label='X'+str(i)+'={value:0.2f}V', 
					labelOpts={'color': (0,200,200), 'movable': True, 'fill': (0, 0, 200, 100)})
				self.cursor[index].setPos([index, index])
				self.addItem(self.cursor[index])

			case 2 | 3:
				ind = index - 1
				self.cursor[index] = pg.InfiniteLine(movable=True, angle=90, label='Y'+str(ind)+'={value:0.2f}ms', 
					labelOpts={'position':0.1, 'color': (200,200,100), 'fill': (200,200,200,50), 'movable': True})
				self.cursor[index].setPos([index*100, index])
				self.addItem(self.cursor[index])'''

		'''if self.cursor[0] and self.cursor[1]:
		    x1_pos, y1_pos = self.cursor[0].getPos()
		    x2_pos, y2_pos = self.cursor[1].getPos()
		    self.cursor[4] = pg.LineSegmentROI([(100, y1_pos), (100, y2_pos) ], movable=False)
		    self.addItem(self.cursor[4])'''

		'''if self.cursor[2] and self.cursor[3]:
		    x1_pos, y1_pos = self.cursor[2].getPos()
		    x2_pos, y2_pos = self.cursor[3].getPos()
		    self.cursor[5] = pg.LineSegmentROI([(x1_pos, 2), (x2_pos, 2) ], pen=(0, 0, 200),  movable=False)
		    self.cursor[5].setLabel("Mój odcinek")
		    self.addItem(self.cursor[5])'''



	def on_plot_timer(self):
		#print("PLOT_TIMER MyGraph")										
		#print (self.dataset_changed)	

		if self.first == True:											# FIRST: CREATE THE PLOTS 
			self.create_plots()	
			print("len(self.plot_refs)")
			print(len(self.plot_refs))
			self.first = False
			print("First plot timer")

		# SECOND: UPDATE THE PLOTS:
		
		if(self.dataset_changed == True):								# redraw only if there are changes on the dataset
			#print("dataset has changed")
			#print("length of subset")
			#print(len(self.plot_subset))
			self.dataset_changed = False
			
			try:
				self.np_dataset = np.matrix(self.dataset[:][-self.max_points:])		# we only use as subset the last max_points
				self.np_dataset_t = self.np_dataset.transpose()
				self.plot_subset = self.np_dataset_t.tolist()


			except:
				pass					 
			
			
			# ~ print("len(self.plot_subset[0])")
			# ~ print(len(self.plot_subset[0]))

			
			# ~ print("self.dataset")
			# ~ print(self.dataset)
			# ~ print("self.np_dataset")
			# ~ print(self.np_dataset)			
			# ~ print("self.plot_subset")
			# ~ for var in self.plot_subset:
				# ~ print(var)	

						
			for i in range(len(self.plot_subset)):
				# ~ print("len(self.plot_refs)")
				# ~ print(len(self.plot_refs))
				if(self.enabled_graphs[i] == True):							
					self.plot_refs[i].setData(self.plot_subset[i]) 		# required for update: reassign references to the plots
				else:
					self.plot_refs[i].setData([])	# empty plot, if toggle not active.
				
				self.dataset_changed = True
			
			pg.QtGui.QGuiApplication.processEvents()						# for whatever reason, works faster when using processEvent.
		

## THIS PART WON'T BE EXECUTED WHEN IMPORTED AS A SUBMODULE, BUT ONLY WHEN TESTED INDEPENDENTLY ##

if __name__ == "__main__":

	class MainWindow(QMainWindow):
		
		# class variables #
		data_tick_ms = 20

		#creating a fixed size dataset #
		dataset = []
	
		# constructor # 
		def __init__(self):
			
			super().__init__()
			
			# add graph and show #
			#self.graph = MyGraph(dataset = self.dataset)
			
			self.plot = MyPlot(dataset = self.dataset)					# extend the constructor, to force giving a reference to a dataset ???
			
			self.plot.start_plotting()
			
			self.data_timer = QTimer()
			self.data_timer.timeout.connect(self.on_data_timer)
			self.data_timer.start(self.data_tick_ms)

			self.plot.check_toggles("all")
			self.plot.enable_toggles("all")
								


			self.setCentralWidget(self.plot)
			# last step is showing the window #
			self.show()
			
			#self.plot.graph.plot_timer.start()
			
		
		def on_data_timer(self):										# simulate data coming from external source at regular rate.
			t0 = time.time()
			logging.debug("length of dataset: " + str(len(self.plot.dataset)))
			
			
			line = []
			for i in range(0,MAX_PLOTS):
					line.append(random.randrange(0,100))	
			self.dataset.append(line)
					
			print("self.dataset")
			for data in self.dataset:
				print(data)
			
			self.plot.dataset = self.dataset							# this SHOULD HAPPEN INTERNAL TO THE CLASS !!!
					
			self.plot.update()
			t = time.time()
			dt = t - t0
			logging.debug("execution time add_stuff_dataset " + str(dt))
			

	app = QApplication([])
	app.setStyle("Fusion")												# required to use it here
	mw = MainWindow()
	app.exec_()

