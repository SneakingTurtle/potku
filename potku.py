# coding=utf-8
"""
Created on 21.3.2013
Updated on 9.4.2018

Potku is a graphical user interface for analyzation and 
visualization of measurement data collected from a ToF-ERD 
telescope. For physics calculations Potku uses external 
analyzation components.  
Copyright (C) Jarkko Aalto, Timo Konu, Samuli Kärkkäinen, Samuli Rahkonen and 
Miika Raunio

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the

GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program (file named 'LICENCE').
"""
__author__ = "Jarkko Aalto \n Timo Konu \n Samuli Kärkkäinen \n Samuli Rahkonen \n Miika Raunio \n" \
             "Severi Jääskeläinen \n Samuel Kaiponen \n Heta Rekilä \n Sinikka Siironen"
__version__ = "2.0"

import gc
import os
import shutil
import sys
import platform
import subprocess
from datetime import datetime, timedelta
from PyQt5 import QtWidgets, QtCore, uic

from dialogs.about import AboutDialog
from dialogs.global_settings import GlobalSettingsDialog
from dialogs.measurement.import_binary import ImportDialogBinary
from dialogs.measurement.import_measurement import ImportMeasurementsDialog
from dialogs.request_settings import RequestSettingsDialog
from dialogs.new_request import RequestNewDialog
from dialogs.simulation.new_simulation import SimulationNewDialog
from modules.general_functions import open_file_dialog
from modules.global_settings import GlobalSettings
from modules.icon_manager import IconManager
from modules.masses import Masses
from modules.request import Request
from widgets.measurement.tab import MeasurementTabWidget
from widgets.simulation.tab import SimulationTabWidget


class Potku(QtWidgets.QMainWindow):
    """Potku is main window class.
    """
    
    def __init__(self):
        """Init main window for Potku.
        """
        super().__init__()
        self.ui = uic.loadUi(os.path.join("ui_files", "ui_main_window.ui"), self)
        self.title = self.ui.windowTitle()
        self.ui.treeWidget.setHeaderLabel("")
        
        self.icon_manager = IconManager()
        self.settings = GlobalSettings()
        self.request = None
        self.masses = Masses(os.path.join("external", "Potku-data", "masses.dat"))
        self.potku_bin_dir = os.getcwd()
        
        # Holds references to all the tab widgets in "tab_measurements" 
        # (even when they are removed from the QTabWidget)
        self.tab_widgets = {}
        self.tab_id = 0  # identification for each tab

        # Set up connections within UI
        self.ui.actionNew_Measurement.triggered.connect(self.open_new_measurement)
        self.ui.requestSettingsButton.clicked.connect(self.open_request_settings)
        self.ui.globalSettingsButton.clicked.connect(self.open_global_settings)
        self.ui.tabs.tabCloseRequested.connect(self.remove_tab)
        self.ui.treeWidget.itemDoubleClicked.connect(self.focus_selected_tab)
        
        self.ui.requestNewButton.clicked.connect(self.make_new_request)
        self.ui.requestOpenButton.clicked.connect(self.open_request)
        self.ui.actionNew_Request.triggered.connect(self.make_new_request)
        self.ui.actionOpen_Request.triggered.connect(self.open_request)
        self.ui.addNewMeasurementButton.clicked.connect(self.open_new_measurement)
        self.ui.actionNew_measurement_2.triggered.connect(self.open_new_measurement)
        self.ui.actionImport_pelletron.triggered.connect(self.import_pelletron)
        self.ui.actionBinary_data_lst.triggered.connect(self.import_binary)
        self.ui.action_manual.triggered.connect(self.__open_manual)
        
        self.ui.actionSave_cuts.triggered.connect(
                                self.current_measurement_save_cuts)
        self.ui.actionAnalyze_elemental_losses.triggered.connect(
                                self.current_measurement_analyze_elemental_losses)
        self.ui.actionCreate_energy_spectrum.triggered.connect(
                                self.current_measurement_create_energy_spectrum)
        self.ui.actionCreate_depth_profile.triggered.connect(
                                self.current_measurement_create_depth_profile)
        self.ui.actionGlobal_Settings.triggered.connect(self.open_global_settings)
        self.ui.actionRequest_Settings.triggered.connect(self.open_request_settings)
        self.ui.actionAbout.triggered.connect(self.open_about_dialog)
        
        self.ui.actionNew_Request_2.triggered.connect(self.make_new_request)
        self.ui.actionOpen_Request_2.triggered.connect(self.open_request)
        self.ui.actionExit.triggered.connect(self.close)
        
        self.ui.menuImport.setEnabled(False)
        self.panel_shown = True
        self.ui.hidePanelButton.clicked.connect(lambda: self.hide_panel())

        # Set up simulation connections within UI
        self.ui.actionNew_Simulation.triggered.connect(self.create_new_simulation)
        self.ui.actionNew_Simulation_2.triggered.connect(self.create_new_simulation)
        self.ui.actionImport_simulation.triggered.connect(self.import_simulation)
        self.ui.actionCreate_energy_spectrum_sim.triggered.connect(self.current_simulation_create_energy_spectrum)
        self.ui.addNewSimulationButton.clicked.connect(self.create_new_simulation)

        # Set up report tool connection in UI
        self.ui.actionCreate_report.triggered.connect(self.create_report)

        # Add the context menu to the treewidget.
        # PyCharm can't find reference, but they do work
        delete_measurement = QtWidgets.QAction("Delete", self.ui.treeWidget)
        delete_measurement.triggered.connect(self.delete_selections)
        master_measurement = QtWidgets.QAction("Make master", self.ui.treeWidget)
        master_measurement.triggered.connect(self.__make_master_measurement)
        master_measurement_rem = QtWidgets.QAction("Remove master", self.ui.treeWidget)
        master_measurement_rem.triggered.connect(self.__remove_master_measurement)
        slave_measurement = QtWidgets.QAction("Exclude from slaves", self.ui.treeWidget)
        slave_measurement.triggered.connect(self.__make_nonslave_measurement)
        slave_measurement_rem = QtWidgets.QAction("Include as slave", self.ui.treeWidget)
        slave_measurement_rem.triggered.connect(self.__make_slave_measurement)
        self.ui.treeWidget.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.ui.treeWidget.addAction(master_measurement)
        self.ui.treeWidget.addAction(master_measurement_rem)
        # self.ui.treeWidget.addSeparator() TODO: This should have separator
        # but doesn't work for QTreeWidget().
        self.ui.treeWidget.addAction(slave_measurement)
        self.ui.treeWidget.addAction(slave_measurement_rem)
        # self.ui.treeWidget.addSeparator() TODO: This should have separator
        # but doesn't work for QTreeWidget().
        self.ui.treeWidget.addAction(delete_measurement)
        
        # Set up styles for main window 
        bg_blue = "images/background_blue.svg"  # Cannot use os.path.join (PyQT+css)
        bg_green = "images/background_green.svg"
        style_intro = "QWidget#introduceTab {border-image: url(" + bg_blue + ");}"
        style_mesinfo = ("QWidget#infoTab {border-image: url(" +
                         bg_green + ");}")
        self.ui.introduceTab.setStyleSheet(style_intro)
        self.ui.infoTab.setStyleSheet(style_mesinfo)
        self.__remove_info_tab()
        
        self.ui.setWindowIcon(self.icon_manager.get_icon("potku_icon.ico"))        
        
        # Set main window's icons to place
        self.__set_icons()
        self.ui.showMaximized()

    def __initialize_top_items(self):
        """
        Makes the top item visible in the tree of the UI.
        """
        self.measurements_item = QtWidgets.QTreeWidgetItem()
        self.simulations_item = QtWidgets.QTreeWidgetItem()
        self.measurements_item.setText(0, "Measurements")
        self.simulations_item.setText(0, "Simulations")
        self.__change_tab_icon(self.measurements_item, "folder_locked.svg")
        self.__change_tab_icon(self.simulations_item, "folder_locked.svg")
        self.ui.treeWidget.addTopLevelItem(self.measurements_item)
        self.ui.treeWidget.addTopLevelItem(self.simulations_item)

    def create_report(self):
        """
        Opens a dialog for making a report.
        """
        # TODO: Replace this with the actual dialog call.
        QtWidgets.QMessageBox.critical(self, "Error", "Report tool not yet implemented!", QtWidgets.QMessageBox.Ok,
                                       QtWidgets.QMessageBox.Ok)

    def current_measurement_create_depth_profile(self):
        """Opens the depth profile analyzation tool for the current open 
        measurement tab widget.
        """
        widget = self.ui.tabs.currentWidget()
        if hasattr(widget, "measurement"):
            widget.open_depth_profile(widget)
        else:
            QtWidgets.QMessageBox.question(self, "Notification", "An open measurement is required to do this action.",
                                           QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok)

    def current_measurement_analyze_elemental_losses(self):
        """Opens the element losses analyzation tool for the current open 
        measurement tab widget.
        """
        widget = self.ui.tabs.currentWidget()
        if hasattr(widget, "measurement"):
            widget.open_element_losses(widget)
        else:
            QtWidgets.QMessageBox.question(self, "Notification", "An open measurement is required to do this action.",
                                           QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok)

    def current_measurement_create_energy_spectrum(self):
        """Opens the energy spectrum analyzation tool for the current open 
        measurement tab widget.
        """
        widget = self.ui.tabs.currentWidget()
        if hasattr(widget, "measurement"):
            widget.open_energy_spectrum(widget)
        else:
            QtWidgets.QMessageBox.question(self, "Notification", "An open measurement is required to do this action.",
                                           QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok)

    def current_measurement_save_cuts(self):
        """Saves the current open measurement tab widget's selected cuts 
        to cut files.
        """
        widget = self.ui.tabs.currentWidget()
        if hasattr(widget, "measurement"):
            widget.measurement_save_cuts()
        else:
            QtWidgets.QMessageBox.question(self, "Notification", "An open measurement is required to do this action.",
                                           QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok)

    def current_simulation_create_energy_spectrum(self):
        """
        Opens the energy spectrum analyzation tool for the current open
        simulation tab widget.
        """
        widget = self.ui.tabs.currentWidget()
        if hasattr(widget, "simulation"):
            widget.open_energy_spectrum(widget)
        else:
            QtWidgets.QMessageBox.question(self, "Notification", "An open simulation is required to do this action.",
                                           QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok)
    
    def delete_selections(self):
        """Deletes the selected tree widget items.
        """
        # TODO: Memory isn't released correctly. Maybe because of matplotlib.
        # TODO: Remove 'measurement_tab_widgets' variable and add tab reference
        # to treewidgetitem.
        selected_tabs = [self.tab_widgets[item.tab_id] for
                         item in self.ui.treeWidget.selectedItems()]
        if selected_tabs:  # Ask user a confirmation.
            reply = QtWidgets.QMessageBox.question(self, "Confirmation", "Deleting selected measurements will delete"
                                                   + " all files and folders under selected measurement directories."
                                                   + "\n\nAre you sure you want to delete selected measurements?",
                                                   QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No |
                                                   QtWidgets.QMessageBox.Cancel,
                                                   QtWidgets.QMessageBox.Cancel)
            if reply == QtWidgets.QMessageBox.No or reply == QtWidgets.QMessageBox.Cancel:
                return  # If clicked Yes, then continue normally
        
        for tab in selected_tabs:
            measurement = self.request.samples.measurements.get_key_value(tab.tab_id)
            try:
                # Close and remove logs
                measurement.remove_and_close_log(measurement.defaultlog)
                measurement.remove_and_close_log(measurement.errorlog)
                
                # Remove measurement's directory tree
                shutil.rmtree(measurement.directory)
                os.remove(os.path.join(self.request.directory,
                                       measurement.measurement_file))
            except:
                print("Error with removing files")
                QtWidgets.QMessageBox.question(self, "Confirmation", "Problem with deleting files.",
                                               QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok)
                measurement.set_loggers()
                return
            
            self.request.samples.measurements.remove_by_tab_id(tab.tab_id)
            remove_index = self.ui.tabs.indexOf(tab)
            self.remove_tab(remove_index)  # Remove measurement from open tabs 
            
            tab.histogram.matplotlib.delete()
            tab.elemental_losses_widget.matplotlib.delete()
            tab.energy_spectrum_widget.matplotlib.delete()
            tab.depth_profile_widget.matplotlib.delete()
            
            tab.mdiArea.closeAllSubWindows()
            del self.tab_widgets[tab.tab_id]
            tab.close() 
            tab.deleteLater()
            
        # Remove selected from tree widget
        root = self.ui.treeWidget.invisibleRootItem()
        for item in self.ui.treeWidget.selectedItems():
            (item.parent() or root).removeChild(item)
        gc.collect()  # Suggest garbage collector to clean.

    def focus_selected_tab(self, clicked_item):
        """Focus to selected tab (in tree widget) and if it isn't open, open it.
        
        Args:
            clicked_item: TreeWidgetItem with tab_id attribute (int) that connects
            the item to the corresponding MeasurementTabWidget
        """
        # TODO: This doesn't work. There is no list/dictionary of references to the
        # tab widgets once they are removed from the QTabWidget. 
        # tab = self.request_measurements[clicked_item.tab_id]
        tab = self.tab_widgets[clicked_item.tab_id]

        if type(tab) is MeasurementTabWidget:
            name = tab.measurement.measurement_name

            # Check that the data is read.
            if not tab.data_loaded:
                tab.data_loaded = True
                progress_bar = QtWidgets.QProgressBar()
                loading_bar = QtWidgets.QProgressBar()
                loading_bar.setMinimum(0)
                loading_bar.setMaximum(0)
                self.statusbar.addWidget(progress_bar, 1)
                self.statusbar.addWidget(loading_bar, 2)
                progress_bar.show()
                loading_bar.show()
                progress_bar.setValue(5)
                QtCore.QCoreApplication.processEvents(QtCore.QEventLoop.AllEvents)

                tab.measurement.load_data()
                progress_bar.setValue(35)
                QtCore.QCoreApplication.processEvents(QtCore.QEventLoop.AllEvents)

                tab.add_histogram()
                loading_bar.hide()
                self.statusbar.removeWidget(loading_bar)

                progress_bar.setValue(50)
                QtCore.QCoreApplication.processEvents(QtCore.QEventLoop.AllEvents)
                tab.check_previous_state_files(progress_bar)  # Load previous states.
                self.statusbar.removeWidget(progress_bar)
                progress_bar.hide()
                self.__change_tab_icon(clicked_item)
                master_mea = tab.measurement.request.get_master()
                if master_mea and tab.measurement.measurement_name == master_mea.measurement_name:
                    name = "{0} (master)".format(name)

        elif type(tab) is SimulationTabWidget:
            name = tab.simulation.name

            # Check that the data is read.
            if not tab.data_loaded:
                tab.data_loaded = True
                tab.simulation.load_data()
                tab.add_simulation_depth_profile()
                self.__change_tab_icon(clicked_item)
        else:
            raise TabError("No such tab widget")
        
        # Check that the tab to be focused exists.
        if not self.__tab_exists(clicked_item.tab_id): 
            self.ui.tabs.addTab(tab, name)
        self.ui.tabs.setCurrentWidget(tab)

    def hide_panel(self, enable_hide=None):
        """Sets the frame (including measurement navigation view, global 
        settings and request settings buttons) visible.
        
        Args:
            enable_hide: If True, sets the frame visible and vice versa. 
            If not given, sets the frame visible or hidden depending its 
            previous state.
        """
        if enable_hide is not None:
            self.panel_shown = enable_hide
        else:
            self.panel_shown = not self.panel_shown    
        if self.panel_shown:
            self.ui.hidePanelButton.setText("<")
        else:
            self.ui.hidePanelButton.setText(">")

        self.ui.frame.setVisible(self.panel_shown)

    def import_pelletron(self):
        """Import Pelletron's measurements into request.
        
        Import Pelletron's measurements from 
        """
        if not self.request:
            return
        import_dialog = ImportMeasurementsDialog(self.request,
                                                 self.icon_manager,
                                                 self.statusbar,
                                                 self)  # For loading measurements.
        if import_dialog.imported:
            self.__remove_info_tab()

    def import_binary(self):
        """Import binary measurements into request.
        
        Import binary measurements from 
        """
        if not self.request:
            return
        import_dialog = ImportDialogBinary(self.request,
                                           self.icon_manager,
                                           self.statusbar,
                                           self)  # For loading measurements.
        if import_dialog.imported:
            self.__remove_info_tab()

    def import_simulation(self):
        """
        Opens a file dialog for selecting simulation to import.
        Opens selected simulation in Potku.
        """
        if not self.request:
            return
        # TODO: What type of file should be opened? This may other method than open_file_dialog
        filename = open_file_dialog(self, self.request.directory, "Select a simulation to load",
                                    "Simulation (*.smthn)")
        # TODO: create necessary tab widget etc.
        if filename:
            QtWidgets.QMessageBox.critical(self, "Error", "Simulation import not yet implemented!",
                                           QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok)

    def load_request_measurements(self, measurements=[]):
        """Load measurement files in the request.
        
        Args:
            measurements: A list representing loadable measurements when importing
                          measurements to the request.
        """
        # TODO: fix this for import_binary.py and import_measurement.py
        if measurements:
            samples_with_measurements = measurements
            load_data = True
        else:
            # a dict with the sample as a key, and measurements in the value as a list
            samples_with_measurements = self.request.samples.get_samples_and_measurements()
            load_data = False
        progress_bar = QtWidgets.QProgressBar()
        self.statusbar.addWidget(progress_bar, 1)
        progress_bar.show()
        
        count = len(samples_with_measurements)
        dirtyinteger = 0
        for sample, measurements in samples_with_measurements.items():
            for measurement_file in measurements:
                self.__add_new_tab("measurement", measurement_file, sample, progress_bar,
                                   dirtyinteger, count, load_data=load_data)
                dirtyinteger += 1

        self.statusbar.removeWidget(progress_bar)
        progress_bar.hide()

    def load_request_samples(self):
        """"Load sample files in the request.
        """
        sample_paths_in_request = self.request.get_samples_files()
        if sample_paths_in_request:
            for sample_path in sample_paths_in_request:
                self.request.samples.add_sample_file(sample_path)
            self.request.increase_running_int_by_1()
        # TODO: update widget tree with the uploaded samples

    def load_request_simulations(self, simulations=[]):
        """Load simulation files in the request.

        Args:
            simulations: A list representing loadable simulation when importing
                          simulation to the request.
        """
        if simulations:
            samples_with_measurements = simulations
            load_data = True
        else:
            samples_with_measurements = self.request.samples.get_samples_and_simulations()
            load_data = False
        progress_bar = QtWidgets.QProgressBar()
        self.statusbar.addWidget(progress_bar, 1)
        progress_bar.show()

        count = len(samples_with_measurements)
        dirtyinteger = 0
        for sample, simulations in samples_with_measurements.items():
            for simulation_file in simulations:
                self.__add_new_tab("simulation", simulation_file, sample, progress_bar,
                                   dirtyinteger, count, load_data=load_data)
                dirtyinteger += 1

        self.statusbar.removeWidget(progress_bar)
        progress_bar.hide()

    def make_new_request(self):
        """Opens a dialog for creating a new request.
        """
        dialog = RequestNewDialog(self)  # The directory for request is already created after this

        # TODO: regex check for directory. I.E. do not allow asd/asd
        if dialog.directory:
            self.__close_request()
            title = "{0} - Request: {1}".format(self.title, dialog.name)
            self.ui.setWindowTitle(title)

            self.ui.treeWidget.setHeaderLabel("Request: {0}".format(dialog.name))
            self.__initialize_top_items()

            self.request = Request(dialog.directory, dialog.name, self.masses,
                                   self.statusbar, self.settings,
                                   self.tab_widgets)
            self.settings.set_request_directory_last_open(dialog.directory)
            # Request made, close introduction tab
            self.__remove_introduction_tab()
            self.__open_info_tab()
            self.__set_request_buttons_enabled(True)

    def open_about_dialog(self):
        """Show Potku program about dialog.
        """
        AboutDialog()

    def open_global_settings(self):
        """Opens global settings dialog.
        """
        GlobalSettingsDialog(self.masses, self.settings)

    def open_new_measurement(self):
        """Opens file an open dialog and if filename is given opens new measurement 
        from it.
        """
        if not self.request:
            return
        filename = open_file_dialog(self,
                                    self.request.directory,
                                    "Select a measurement to load",
                                    "Raw Measurement (*.asc)")
        if filename:
            try:
                self.ui.tabs.removeTab(self.ui.tabs.indexOf(
                                                   self.measurement_info_tab))
            except: 
                pass  # If there is no info tab, no need to worry about.
                # print("Can't find an info tab to remove")
            progress_bar = QtWidgets.QProgressBar()
            self.statusbar.addWidget(progress_bar, 1)
            progress_bar.show()

            name_prefix = "Sample_"
            sample_path = os.path.join(self.request.directory, name_prefix + self.request.get_running_int())
            new_sample = self.request.samples.add_sample_file(sample_path)
            self.request.increase_running_int_by_1()

            self.__add_new_tab("measurement", filename, new_sample, progress_bar, load_data=True)
            self.__remove_info_tab()
            self.statusbar.removeWidget(progress_bar)
            progress_bar.hide()

    def create_new_simulation(self):
        """
        Opens a dialog for creating a new simulation.
        """
        dialog = SimulationNewDialog()

        # filename = dialog.name
        # if filename:
        #     try:
        #         self.ui.tabs.removeTab(self.ui.tabs.indexOf(
        #             self.measurement_info_tab))
        #     except:
        #         pass  # If there is no info tab, no need to worry about.
        #         # print("Can't find an info tab to remove")
        #
        simulation_name = dialog.name
        if simulation_name:
            progress_bar = QtWidgets.QProgressBar()
            self.statusbar.addWidget(progress_bar, 1)
            progress_bar.show()

            # self.__add_new_tab("simulation", filename, progress_bar, load_data=False)
            # self.__add_new_tab("simulation", "tiedosto", progress_bar, load_data=False)
            name_prefix = "Sample_"
            sample_path = os.path.join(self.request.directory, name_prefix + self.request.get_running_int())
            new_sample = self.request.samples.add_sample_file(sample_path)

            self.__add_new_tab("simulation", dialog.name, new_sample, progress_bar, load_data=False)
            self.__remove_info_tab()
            self.statusbar.removeWidget(progress_bar)
            progress_bar.hide()

    def open_request(self):
        """Shows a dialog to open a request.
        """
        file = open_file_dialog(self,
                                self.settings.get_request_directory_last_open(),
                                "Open an existing request", "Request file (*.request)")
        if file:
            self.__close_request()
            folder = os.path.split(file)[0]
            folders = folder.split("/")
            fd_with_correct_sep = os.sep.join(folders)
            tmp_name = os.path.splitext(os.path.basename(file))[0]
            self.request = Request(fd_with_correct_sep, tmp_name, self.masses,
                                   self.statusbar, self.settings,
                                   self.tab_widgets)
            self.ui.setWindowTitle("{0} - Request: {1}".format(
                                                       self.title,
                                                       self.request.get_name()))
            self.ui.treeWidget.setHeaderLabel(
                                 "Request: {0}".format(self.request.get_name()))
            self.__initialize_top_items()
            self.settings.set_request_directory_last_open(folder)

            self.load_request_samples()
            self.load_request_measurements()
            self.load_request_simulations()
            self.__remove_introduction_tab()
            self.__set_request_buttons_enabled(True)
            
            master_measurement_name = self.request.has_master()
            nonslaves = self.request.get_nonslaves()
            if master_measurement_name:
                master_measurement = None
                keys = self.request.samples.measurements.measurements.keys()
                for key in keys:
                    measurement = self.request.samples.measurements.measurements[key]
                    if measurement.measurement_name == master_measurement_name:
                        master_measurement = measurement
                        self.request.set_master(measurement)
                        break
            root = self.treeWidget.invisibleRootItem()
            # root_child_count = root.childCount()
            measurement_items = root.child(0)
            simulation_items = root.child(1)

            for i in range(measurement_items.childCount()):
                item = measurement_items.child(i)
                tab_widget = self.tab_widgets[item.tab_id]
                tab_name = tab_widget.measurement.measurement_name
                if master_measurement_name and \
                   item.tab_id == master_measurement.tab_id:
                    item.setText(0,
                                 "{0} (master)".format(master_measurement_name))
                elif tab_name in nonslaves or not master_measurement_name:
                    item.setText(0, tab_name)
                else:
                    item.setText(0, "{0} (slave)".format(tab_name))

            for i in range(simulation_items.childCount()):
                item = root.child(i)
                tab_widget = self.tab_widgets[item.tab_id]
                tab_name = tab_widget.simulation.name
                item.setText(0, tab_name)

    def open_request_settings(self):
        """Opens request settings dialog.
        """
        RequestSettingsDialog(self.masses, self.request)

    def remove_tab(self, tab_index):
        """Remove tab which's close button has been pressed.
        
        Args:
            tab_index: Integer representing index of the current tab
        """
        self.ui.tabs.removeTab(tab_index)

    def __add_measurement_to_tree(self, measurement_name, load_data):
        """Add measurement to tree where it can be opened.
        
        Args:
            measurement_name: A string representing measurement's name.
            load_data: A boolean representing if measurement data is loaded.
        """
        tree_item = QtWidgets.QTreeWidgetItem()
        tree_item.setText(0, measurement_name)
        tree_item.tab_id = self.tab_id
        # tree_item.setIcon(0, self.icon_manager.get_icon("folder_open.svg"))
        if load_data:
            self.__change_tab_icon(tree_item, "folder_open.svg")
        else:
            self.__change_tab_icon(tree_item, "folder_locked.svg")
        # self.ui.treeWidget.addTopLevelItem(tree_item)
        self.measurements_item.addChild(tree_item)

    def __add_simulation_to_tree(self, simulation_name, load_data):
        """Add measurement to tree where it can be opened.

        Args:
            measurement_name: A string representing measurement's name.
            load_data: A boolean representing if measurement data is loaded.
        """
        tree_item = QtWidgets.QTreeWidgetItem()
        tree_item.setText(0, simulation_name)
        tree_item.tab_id = self.tab_id
        # tree_item.setIcon(0, self.icon_manager.get_icon("folder_open.svg"))
        if load_data:
            self.__change_tab_icon(tree_item, "folder_open.svg")
        else:
            self.__change_tab_icon(tree_item, "folder_locked.svg")
        self.ui.treeWidget.addTopLevelItem(tree_item)
        self.simulations_item.addChild(tree_item)

    def __add_new_tab(self, tab_type, filename, sample, progress_bar=None,
                      file_current=0, file_count=1, load_data=False):
        """Add new tab into TabWidget. TODO: Simulation included. Should be changed.
        
        Adds a new tab into program's tabWidget. Makes a new measurement for 
        said tab.
        
        Args:
            tab_type: Either "measurement" or "simulation".
            filename: A string representing measurement file.
            sample: The sample under which the measurement or simulation is put.
            progress_bar: A QtWidgets.QProgressBar to be updated.
            file_current: An integer representing which number is currently being
                          read. (for GUI)
            file_count: An integer representing how many files will be loaded.
            load_data: A boolean representing whether to load data or not. This is
                       to save time when loading a request and we do not want to
                       load every measurement.
        """
        if progress_bar:
            progress_bar.setValue((100 / file_count) * file_current)
            QtCore.QCoreApplication.processEvents(QtCore.QEventLoop.AllEvents)

        if tab_type == "measurement":
            measurement = self.request.samples.measurements.add_measurement_file(sample, filename, self.tab_id)
            sample.increase_running_int_measurement_by_1()
            if measurement:  # TODO: Finish this (load_data)
                tab = MeasurementTabWidget(self.tab_id, measurement,
                                           self.masses, self.icon_manager)
                tab.issueMaster.connect(self.__master_issue_commands)

                tab.setAttribute(QtCore.Qt.WA_DeleteOnClose)
                self.tab_widgets[self.tab_id] = tab
                tab.add_log()
                tab.data_loaded = load_data
                if load_data:
                    loading_bar = QtWidgets.QProgressBar()
                    loading_bar.setMinimum(0)
                    loading_bar.setMaximum(0)
                    self.statusbar.addWidget(loading_bar, 1)
                    loading_bar.show()

                    measurement.load_data()
                    tab.add_histogram()
                    self.ui.tabs.addTab(tab, measurement.measurement_name)
                    self.ui.tabs.setCurrentWidget(tab)

                    loading_bar.hide()
                    self.statusbar.removeWidget(loading_bar)
                self.__add_measurement_to_tree(measurement.measurement_name, load_data)
                self.tab_id += 1

        if tab_type == "simulation":
            simulation = self.request.samples.simulations.add_simulation_file(sample, filename, self.tab_id)
            sample.increase_running_int_simulation_by_1()

            if simulation:  # TODO: Finish this (load_data)
                tab = SimulationTabWidget(self.request, self.tab_id, simulation,
                                          self.masses, self.icon_manager)
                tab.issueMaster.connect(self.__master_issue_commands)

                tab.setAttribute(QtCore.Qt.WA_DeleteOnClose)
                self.tab_widgets[self.tab_id] = tab
                # tab.add_log()
                tab.data_loaded = load_data
                if load_data:
                    simulation.load_data()
                    tab.add_simulation_depth_profile()
                    self.ui.tabs.addTab(tab, simulation.name)
                    self.ui.tabs.setCurrentWidget(tab)

                self.__add_simulation_to_tree(simulation.name, load_data)
                self.tab_id += 1

    def __change_tab_icon(self, tree_item, icon="folder_open.svg"):
        """Change tab icon in QTreeWidgetItem.
        
        Args:
            tree_item: A QtWidgets.QTreeWidgetItem class object.
            icon: A string representing the icon name.
        """
        tree_item.setIcon(0, self.icon_manager.get_icon(icon))

    def __close_request(self):
        """Closes the request for opening a new one.
        """
        if self.request:
            # TODO: Doesn't release memory
            # Clear the treewidget
            self.ui.treeWidget.clear()
            self.ui.tabs.clear()
            self.request = None
            self.tab_widgets = {}
            self.tab_id = 0

    def __make_nonslave_measurement(self):
        """Exclude selected measurements from slave category.
        """
        items = self.ui.treeWidget.selectedItems()
        if not items:
            return
        master = self.request.get_master()
        # Remove (slave) text from tree titles
        for item in items:
            tab_widget = self.tab_widgets[item.tab_id]
            tabs = tab_widget.measurement
            tab_name = tabs.measurement_name
            if master and tab_name != master.measurement_name:
                self.request.exclude_slave(tabs)
                item.setText(0, tab_name)

    def __make_slave_measurement(self):
        """Exclude selected measurements from slave category.
        """
        items = self.ui.treeWidget.selectedItems()
        if not items:
            return
        master = self.request.get_master()
        # Add (slave) text from tree titles
        for item in items:
            tab_widget = self.tab_widgets[item.tab_id]
            tabs = tab_widget.measurement
            tab_name = tabs.measurement_name
            if master and tab_name != master.measurement_name:
                self.request.include_slave(tabs)
                item.setText(0, "{0} (slave)".format(tab_name))

    def __make_master_measurement(self):
        """Make selected or first of the selected measurements 
        a master measurement.
        """
        items = self.ui.treeWidget.selectedItems()
        if not items:
            return
        master_tree = items[0]
        master_tab = self.tab_widgets[master_tree.tab_id]
        self.request.set_master(master_tab.measurement)
        # old_master = self.request.get_master()
        nonslaves = self.request.get_nonslaves()
        
        # if old_master:
        #    old_master_name = old_master.measurement_name
        #    self.ui.tab_measurements.setTabText(old_master.tab_id, old_master_name)
        root = self.treeWidget.invisibleRootItem()
        root_child_count = root.childCount()
        for i in range(root_child_count):
            item = root.child(i)
            tab_widget = self.tab_widgets[item.tab_id]
            tab_name = tab_widget.measurement.measurement_name
            if item.tab_id == master_tab.tab_id:
                item.setText(0, "{0} (master)".format(tab_name))
            elif tab_name in nonslaves:
                item.setText(0, tab_name)
            else:
                item.setText(0, "{0} (slave)".format(tab_name))
            tab_widget.toggle_master_button()
        # master_tab.toggle_master_button()
        # QtGui.QTabWidget().count()
        for i in range(self.ui.tabs.count()):
            tab = self.ui.tabs.widget(i)
            tab_name = tab.measurement.measurement_name
            if tab.tab_id == master_tab.tab_id:
                tab_name = "{0} (master)".format(tab_name)
                self.ui.tabs.setTabText(tab.tab_id, tab_name)
            else:
                self.ui.tabs.setTabText(tab.tab_id, tab_name)

    def __master_issue_commands(self):
        """Issue commands from master measurement to all slave measurements in 
        the request.
        """
        reply = QtWidgets.QMessageBox.question(self, "Confirmation", "You are about to issue actions from master " +
                                               "measurement to all slave measurements in the request. This can take " +
                                               "several minutes. Please wait until notification is shown." +
                                               "\nDo you wish to continue?", QtWidgets.QMessageBox.Yes |
                                               QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.Yes)
        if reply == QtWidgets.QMessageBox.No:
            return
        
        time_start = datetime.now()
        progress_bar = QtWidgets.QProgressBar()
        self.statusbar.addWidget(progress_bar, 1)
        progress_bar.show()
        nonslaves = self.request.get_nonslaves()
        master = self.request.get_master()
        master_tab = self.tab_widgets[master.tab_id]
        master_name = master.measurement_name
        directory = master.directory
        progress_bar.setValue(1)
        QtCore.QCoreApplication.processEvents(QtCore.QEventLoop.AllEvents) 
        # Load selections and save cut files
        # TODO: Make a check for these if identical already -> don't redo.
        self.request.save_selection(master)
        progress_bar.setValue(10)
        QtCore.QCoreApplication.processEvents(QtCore.QEventLoop.AllEvents) 
        
        self.request.save_cuts(master)
        progress_bar.setValue(25)
        QtCore.QCoreApplication.processEvents(QtCore.QEventLoop.AllEvents) 
        
        root = self.treeWidget.invisibleRootItem()
        root_child_count = root.childCount()
        i = 1
        for i in range(root_child_count):
            item = root.child(i)
            tab = self.tab_widgets[item.tab_id]
            tabs = tab.measurement
            tab_name = tabs.measurement_name
            if tab_name == master_name or tab_name in nonslaves:
                continue
            # Load measurement data if the slave is
            if not tab.data_loaded:
                tab.data_loaded = True
                progress_bar_data = QtWidgets.QProgressBar()
                self.statusbar.addWidget(progress_bar_data, 1)
                progress_bar_data.show()
                progress_bar_data.setValue(5)
                QtCore.QCoreApplication.processEvents(QtCore.QEventLoop.AllEvents) 
                
                tab.measurement.load_data()
                progress_bar_data.setValue(35)
                QtCore.QCoreApplication.processEvents(QtCore.QEventLoop.AllEvents) 
                
                tab.add_histogram()
                progress_bar_data.hide()
                self.statusbar.removeWidget(progress_bar_data)
                QtCore.QCoreApplication.processEvents(QtCore.QEventLoop.AllEvents)
                # Update tree item icon to open folder
                tree_item = None
                root = self.treeWidget.invisibleRootItem()
                root_child_count = root.childCount()
                for j in range(root_child_count):
                    item = root.child(j)
                    if item.tab_id == tab.tab_id:
                        tree_item = item
                        break
                if tree_item:
                    self.__change_tab_icon(tree_item)
            # Check all widgets of master and do them for slaves.
            if master_tab.depth_profile_widget and tab.data_loaded:
                if tab.depth_profile_widget:
                    tab.del_widget(tab.depth_profile_widget)
                tab.make_depth_profile(directory, master_name)
                tab.depth_profile_widget.save_to_file()
            if master_tab.elemental_losses_widget and tab.data_loaded:
                if tab.elemental_losses_widget:
                    tab.del_widget(tab.elemental_losses_widget)
                tab.make_elemental_losses(directory, master_name)
                tab.elemental_losses_widget.save_to_file()
            if master_tab.energy_spectrum_widget and tab.data_loaded:
                if tab.energy_spectrum_widget:
                    tab.del_widget(tab.energy_spectrum_widget)
                tab.make_energy_spectrum(directory, master_name)
                tab.energy_spectrum_widget.save_to_file()
            progress_bar.setValue(25 + (i / root_child_count) * 75)
            QtCore.QCoreApplication.processEvents(QtCore.QEventLoop.AllEvents)
            i += 1
        self.statusbar.removeWidget(progress_bar)
        progress_bar.hide()
        time_end = datetime.now()
        time_duration = (time_end - time_start).seconds
        time_str = timedelta(seconds=time_duration)
        QtWidgets.QMessageBox.question(self, "Notification", "Master measurement's actions have been issued to slaves. "
                                       + "\nElapsed time: {0}".format(time_str), QtWidgets.QMessageBox.Ok,
                                       QtWidgets.QMessageBox.Ok)

    def __open_info_tab(self):
        """Opens an info tab to the QTabWidget 'tab_measurements' that guides the 
        user to add a new measurement to the request.
        """
        self.ui.tabs.addTab(self.ui.infoTab, "Info")

    def __remove_introduction_tab(self):
        """Removes an info tab from the QTabWidget 'tab_measurements' that guides
        the user to create a new request.
        """
        index = self.ui.tabs.indexOf(self.ui.introduceTab)
        if index >= 0:
            self.ui.tabs.removeTab(index)

    def __remove_master_measurement(self):
        """Remove master measurement
        """
        old_master = self.request.get_master()
        self.request.set_master()  # No master measurement
        root = self.treeWidget.invisibleRootItem()
        root_child_count = root.childCount()
        for i in range(root_child_count):
            item = root.child(i)
            tab_widget = self.tab_widgets[item.tab_id]
            tab_name = tab_widget.measurement.measurement_name
            item.setText(0, tab_name)
            tab_widget.toggle_master_button()
        if old_master:
            measurement_name = old_master.measurement_name
            self.ui.tabs.setTabText(old_master.tab_id, measurement_name)
            old_master_tab = self.tab_widgets[old_master.tab_id]
            old_master_tab.toggle_master_button()
        self.request.set_master()  # No master measurement

    def __remove_info_tab(self):
        """Removes an info tab from the QTabWidget 'tab_measurements' that guides
        the user to add a new measurement to the request.
        """
        index = self.ui.tabs.indexOf(self.ui.infoTab)
        if index >= 0:
            self.ui.tabs.removeTab(index)

    def __set_icons(self):
        """Adds icons to the main window.
        """
        self.icon_manager.set_icon(self.ui.requestSettingsButton, "gear.svg")
        self.icon_manager.set_icon(self.ui.globalSettingsButton, "gear.svg")
        self.icon_manager.set_icon(self.ui.actionNew_Request, "file.svg")
        self.icon_manager.set_icon(self.ui.actionOpen_Request, "folder_open.svg")
        self.icon_manager.set_icon(self.ui.actionSave_Request, "amarok_save.svg")
        self.icon_manager.set_icon(self.ui.actionNew_Measurement, "log.svg")

    def __set_request_buttons_enabled(self, state=False):
        """Enables 'request settings', 'save request' and 'new measurement' buttons.
           Enables simulation related buttons.
        Args:
            state: True/False enables or disables buttons
        """
        self.ui.requestSettingsButton.setEnabled(state)
        self.ui.actionSave_Request.setEnabled(state)
        self.ui.actionNew_Measurement.setEnabled(state)
        self.ui.actionNew_measurement_2.setEnabled(state)
        self.ui.menuImport.setEnabled(state)
        self.ui.actionRequest_Settings.setEnabled(state)
        # TODO: Should these only be enabled when there is measurement open?
        self.ui.actionAnalyze_elemental_losses.setEnabled(state)
        self.ui.actionCreate_energy_spectrum.setEnabled(state)
        self.ui.actionCreate_depth_profile.setEnabled(state)

        # enable simulation buttons
        self.ui.actionNew_Simulation.setEnabled(state)
        self.ui.actionNew_Simulation_2.setEnabled(state)
        self.ui.actionImport_simulation.setEnabled(state)

        # enable simulation energy spectra button
        self.ui.actionCreate_energy_spectrum_sim.setEnabled(state)

    def __tab_exists(self, tab_id):
        """Check if there is an open tab with the tab_id (identifier).
        
        Args:
            tab_id: Identifier (int) for the MeasurementTabWidget
            
        Returns:
            True if tab is found, False if not
        """
        # Try to find the clicked item from QTabWidget.
        for i in range(0, self.ui.tabs.count()):
            if self.ui.tabs.widget(i).tab_id == tab_id:
                return True
        return False

    def __open_manual(self):
        """Open user manual.
        """
        manual_filename = os.path.join("manual", "Potku-manual.pdf")
        used_os = platform.system()
        try:
            if used_os == "Windows":
                os.startfile(manual_filename)
            elif used_os == "Linux":
                subprocess.call(("xdg-open", manual_filename))
            elif used_os == "Darwin":
                subprocess.call(("open", manual_filename))
        except FileNotFoundError:
            QtWidgets.QMessageBox.question(self, "Not found", "There is no manual to be found!",
                                           QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok)


def main():
    """Main function
    """
    app = QtWidgets.QApplication(sys.argv)
    window = Potku()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
