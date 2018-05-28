# coding=utf-8
"""
Created on 15.3.2013
Updated on 5.3.2018

Potku is a graphical user interface for analyzation and
visualization of measurement data collected from a ToF-ERD
telescope. For physics calculations Potku uses external
analyzation components.
Copyright (C) Severi Jääskeläinen, Samuel Kaiponen, Heta Rekilä and
Sinikka Siironen

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
__author__ = "Severi Jääskeläinen \n Samuel Kaiponen \n Heta Rekilä \n Sinikka Siironen"
__versio__ = "2.0"

from os.path import join
from PyQt5 import QtCore, QtGui, uic, QtWidgets

from dialogs.element_selection import ElementSelectionDialog
import modules.masses as masses


class RecoilElementSelectionDialog(QtWidgets.QDialog):
    """Selection Settings dialog handles showing settings for selection made in
    measurement (in matplotlib graph).
    """

    def __init__(self, recoil_atom_distribution):
        """Inits simulation elemenet selection dialog.
        """
        super().__init__()
        self.ui = uic.loadUi(join("ui_files", "ui_recoil_element_selection_dialog.ui"), self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.recoil_atom_distribution = recoil_atom_distribution

        # Setup connections
        self.ui.element_button.clicked.connect(self.__change_sample_element)
        self.ui.isotope_radio.toggled.connect(self.__toggle_isotope_sample)

        self.ui.OKButton.clicked.connect(self.__accept_settings)
        self.ui.cancelButton.clicked.connect(self.close)

        self.element = None
        self.isotope = None

        # Set current values to UI and show
        #self.__set_values_to_dialog()
        # Whether we accept or cancel selection, then remove selection if cancel.
        self.isOk = False
        self.exec_()

    def __change_sample_element(self):
        """Shows dialog to change selection element.
        """
        self.__change_element(self.ui.element_button,
                              self.ui.isotope_combobox,
                              self.ui.standard_mass_label,
                              self.ui.standard_mass_radio,
                              self.ui.isotope_radio)
        self.__check_if_settings_ok()

    def __change_element(self, button, isotope_combobox, standard_mass_label,
                         standard_mass_radio, isotope_radio,
                         sample=True):
        """Shows dialog to change selection element.

        Args:
            button: QtWidgets.QPushButton (button to select element)
            isotope_combobox: QtWidgets.QComboBox
            isotope_radio: QtGui.QRadioButton
            standard_mass_radio: QtGui.QRadioButton
            standard_mass_label: QtWidgets.QLabel
        """
        dialog = ElementSelectionDialog()
        # Only disable these once, not if you cancel after selecting once.
        if button.text() == "Select":
            isotope_radio.setEnabled(False)
            standard_mass_radio.setEnabled(False)
            standard_mass_label.setEnabled(False)
        # If element was selected, proceed to enable appropriate fields.
        if dialog.element:
            button.setText(dialog.element)
            self.__enable_element_fields(dialog.element, isotope_combobox,
                                         isotope_radio, standard_mass_radio,
                                         standard_mass_label, sample)

    def __enable_element_fields(self, element, isotope_combobox,
                                isotope_radio, standard_mass_radio,
                                standard_mass_label, sample=True,
                                current_isotope=None):
        """Enable element information fields.

        Args:
            element: String representing element.
            isotope_combobox: QtWidgets.QComboBox
            isotope_radio: QtGui.QRadioButton
            standard_mass_radio: QtGui.QRadioButton
            standard_mass_label: QtWidgets.QLabel
            sample: Boolean representing if element is sample (and not RBS element).
        """
        if element:
            isotope_radio.setEnabled(True)
            standard_mass_radio.setEnabled(True)
            standard_mass_label.setEnabled(True)
            self.__load_isotopes(isotope_combobox,
                                 standard_mass_label,
                                 element,
                                 current_isotope)

    def __load_isotopes(self, combobox, standard_mass_label,
                        element, current_isotope=None):
        """Change isotope information regarding element

        Args:
            combobox: QtWidgets.QComboBox where element's isotopes are loaded to.
            standard_mass_label: QtWidgets.QLabel where element's standard mass is shown.
            element: String representing element.
            current_isotope: String representing current isotope.
        """
        standard_mass = masses.get_standard_isotope(element)
        standard_mass_label.setText(str(round(standard_mass, 3)))
        masses.load_isotopes(element, combobox, current_isotope)

    def __toggle_isotope_sample(self):
        """Toggle Sample isotope radio button.
        """
        self.ui.isotope_combobox.setEnabled(self.ui.isotope_radio.isChecked())
    # def __set_isotope_weight_factor(self, isotope_combobox=None):
    #     """Set a specific isotope's weight factor to label.
    #
    #     Args:
    #         isotope_combobox: A QtWidgets.QComboBox element of isotopes.
    #     """
    #     if not isotope_combobox or not isotope_combobox.isEnabled():
    #         self.ui.isotope_specific_weight_factor_label.setText("")
    #     else:
    #         isotope_index = isotope_combobox.currentIndex()
    #         unused_isotope, propability = isotope_combobox.itemData(
    #             isotope_index)
    #         isotope_weightfactor = 100.0 / float(propability)
    #         text = "%.3f for specific isotope" % isotope_weightfactor
    #         self.ui.isotope_specific_weight_factor_label.setText(text)

    def __check_if_settings_ok(self):
        """Check if sample settings are ok, and enable ok button.
        """
        element = self.ui.element_button.text()
        if element:
            self.ui.OKButton.setEnabled(True)
        elif element != "Select" and element:
            self.ui.OKButton.setEnabled(True)
        else:
            self.ui.OKButton.setEnabled(False)

    def __accept_settings(self):
        """Accept settings given in the selection dialog and save these to parent.
        """
        self.element = self.ui.element_button.text()

        # For standard isotopes:

        # Check if specific isotope was chosen and use that instead.
        if self.ui.isotope_radio.isChecked():
            isotope_index = self.ui.isotope_combobox.currentIndex()
            isotope_data = self.ui.isotope_combobox.itemData(isotope_index)
            self.isotope = isotope_data[0]
            # sample_isotope = self.ui.sample_isotope_combobox.currentText()

        self.isOk = True
        self.close()

