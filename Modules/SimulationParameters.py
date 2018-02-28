# TODO: Add licence information
# coding=utf-8
'''
Created on 26.2.2018
Updated on 27.2.2018
'''

import os, logging

class SimulationParameters:

    def __init__(self, file_path):
        self.read_parameters(file_path)

    def read_parameters(self, file_path):
        """ Read the MCERD command file

        Args:
            file_path: An absolute file path to MCERD command file
        """

        # Initialize few simulation parameters. The key values are used later on
        # for checking if a line starts with that specific key. These are
        # the same as in MCERDs read_input.h header file.
        self.simulation = {
            "Type of simulation:": None,
            "Beam ion:": None,
            "Beam energy:": None,
            "Target description file:": None,
            "Detector description file:": None,
            "Recoiling atom:": None,
            "Recoiling material distribution:": None,
            "Target angle:": None,
            "Beam spot size:": None,
            "Minimum angle of scattering:": None,
            "Minimum energy of ions:": None,
            "Number of ions:": None,
            "Number of ions in the presimulation:": None,
            "Average number of recoils per primary ion:": None,
            "Seed number of the random number generator:": None,
            "Recoil angle width (wide or narrow):": None,
            "Minimum main scattering angle:": None,
            "Beam divergence:": None,
            "Beam profile:": None,
            "Surface topography file:": None,
            "Side length of the surface topography image:": None,
            "Number of real ions per each scaling ion:": None
        })

        try:
            with open(file_path) as file:
                lines = file.readlines()  # Read all lines of the file to list
            for line in lines:

                # Check if the current line starts with any of the keys in
                # simulation dictionary. If not, the line is just skipped.
                for key in self.simulation:
                    if line.startswith(key):
                        val = line.partition(':')[2].strip().split()

                        # Some of the parameters in command file have more than
                        # one values. Also, some of them have units, e.g.
                        # "10 deg", so we just want to ignore the units.
                        if len(val) < 3:
                            self.simulation[key] = val[0]
                        else:
                            self.simulation[key] = (val[0], val[1])

            # In the command file there are several other file paths specified.
            # There are the target and detector description files and
            # recoiling material distribution file.
            self.read_layers(self.simulation["Target description file:"])
            self.read_detector_file(
                self.simulation["Detector description file:"])
            self.read_recoiling_material_distribution(
                self.simulation["Recoiling material distribution:"])

        # If we cannot read the command file, we except an IOError
        except IOError:
            # TODO: Print to the project log
            print("Cannot read file " + file_path)
            # msg = 'The file {0} doesn'
            # logging.getLogger('project').error('')

    def read_layers(self, file_path):
        """
        Read MCERD target description file or a description file for detector
        foils. Both files should have similar format.

        Args:
            file_path: An absolute file path. Either target description file or
            a description file for detector foils.
        """
        try:
            with open(file_path) as file:
                elements = []
                layers = []
                line = file.readline()

                # The first few lines should specify the elements
                while line != "\n":
                    elements.append(line.strip())
                    line = file.readline()

                # Currently it's assumed that there's exactly one empty line
                # here. !!! TODO: It might be a good idea to change this

                # Read all the different layers one by one
                while line != "":
                    tmp = {}
                    amount = []
                    tmp["thickness"] = file.readline().strip()
                    tmp["stopping power for beam"] = file.readline().strip()
                    tmp["stopping power for recoil"] = file.readline().strip()
                    tmp["density"] = file.readline().strip()
                    line = file.readline()
                    while line != "\n" and line != "":
                        amount.append(line.strip())
                        line = file.readline()
                    tmp["amount"] = amount
                    layers.append(tmp)

                # The file can be either target description file or
                # description file for detectors foils, so function should
                # check which one is it, so it can save the parameters
                # to right attributes.
                file_name = os.path.splitext(file_path)
                try:
                    if file_name[0] == "target" or file_name[1] == ".target":
                        self.simulation["target"] = {}
                        self.simulation["target"]["elements"] = elements
                        self.simulation["target"]["layers"] = layers
                    elif os.path.splitext(file_path)[1] == ".foils":
                        self.detector["foils"]["elements"] = elements
                        self.detector["foils"]["layers"] = layers
                    else:
                        # If the file is neither of these, the function should
                        # raise an error.
                        raise ValueError("File extension should be either "
                                         "'.target' or '.foils'")
                except:
            # TODO: Print to the project log

        except IOError:
            # TODO: Print to the project log
            print("The file " + file_path + " doesn't exist. ")

    def read_detector_file(self, file_path):
        """ Read MCERD detector description file.

        Args:
            An absolute file path to MCERD decector description file
        """

        # Initialize few detector parameters. These parameters should be
        # located in the beginning of the detector description file.
        self.simulation["detector"] = {
            "Detector type:": None,
            "Detector angle:": None,
            "Virtual detector size:": None,
            "Timing detector numbers:": None,
            "Description file for the detector foils:": None
        }

        # This list is not saved in detectors attributes. It is just used
        # later for checking line beginnings in a file.
        foils = ["Foil type:", "Foil diameter:", "Foil size:", "Foil distance:"]

        try:
            with open(file_path) as file:
                line = file.readline()
                while line != "":

                    # Here we check if the current line starts with any of the
                    # keys in the simulation["detector"] dictionary.
                    for key in self.simulation["detector"]:
                        if line.startswith(key):
                            val = line.partition(':')[2].strip()
                            self.simulation["detector"][key] = val
                            break

                    # Stop if we have all five first parameters in the
                    # dictionary
                    if not (None in self.simulation["detector"].values()):
                        break
                    line = file.readline()

                # Skip empty lines and lines that doesn't have any necessary
                # information.
                while line != "":
                    for key in foils:
                        if not line.startswith(key):
                            line = file.readline()
                            continue
                    break

                self.simulation["detector"]["foils"] = {}
                dimensions = []

                while line != "":

                    tmp = {}

                    # Here we except that the foil dimensions (foil type, foil
                    # diameter/foil size, foil distance) are in groups of three
                    # lines in the description file.
                    for i in range(0, 3):
                        for key in foils:
                            if line.startswith(key):
                                val = line.partition(':')[2].strip()
                                tmp[key] = val
                                break
                        line = file.readline()
                    dimensions.append(tmp)

                    # Skip empty lines and lines that doesn't have any necessary
                    # information.
                    while line != "":
                        for key in foils:
                            if not line.startswith(key):
                                line = file.readline()
                                continue
                        break
                self.read_layers(
                    self.detector["Description file for the detector foils:"])
                self.simulation["detector"]["foils"]["dimensions"] = dimensions

        except IOError as e:
            print(e)

    def read_recoiling_material_distribution(self, file_path):
        """ Read recoiling material distribution

        Args:
            file_path: An aboslute file path to recoiling material distribution
            file.
        """
        try:
            with open(file_path) as file:
                lines = file.readlines()
                self.simulation["recoil"] = []
                # We simply read the recoiling material distribution
                # coordinates to a list.
            for line in lines:
                self.simulation["recoil"].append(line.strip().split())

        except IOError:
            # TODO: Print to the project log
            print("Cannot read file" + file_path)
            # msg = 'The file {0} doesn'
            # logging.getLogger('project').error('')



    def save_foil_params(self, foilsname, filepath):
        """Writes the foil parameters into a file.

        Args:
            foilsname: Name of the file the parameters are written to.
            filepath: Path to the file.
        """
        foil_elements = ["12.011 C", "14.00 N", "28.09 Si"]
        foil_layers = [
            {"thickness": "0.1 nm", "stopping power for beam": "ZBL", "stopping power for recoil": "ZBL",
             "density": "0.1 g/cm3", "amount": ["0 1.0"]},
            {"thickness": "13.3 nm", "stopping power for beam": "ZBL", "stopping power for recoil": "ZBL",
             "density": "2.25 g/cm3", "amount": ["0 1.0"]},
            {"thickness": "44.4 nm", "stopping power for beam": "ZBL", "stopping power for recoil": "ZBL",
             "density": "2.25 g/cm3", "amount": ["0 1.0"]},
            {"thickness": "1.0 nm", "stopping power for beam": "ZBL", "stopping power for recoil": "ZBL",
             "density": "3.44 g/cm3", "amount": ["1 0.57", "2 0.43"]}
        ]

        # form the list that will be written to the file
        foil_list = []
        for elem in foil_elements:
            foil_list.append(elem)
            foil_list.append("\n")

        foil_list.append("\n")

        for layer in foil_layers:
            thickness = layer.get("thickness")
            spfb = layer.get("stopping power for beam")
            spfr = layer.get("stopping power for recoil")
            density = layer.get("density")
            amount = layer.get("amount")

            foil_list.append(thickness + "\n")
            foil_list.append(spfb + "\n")
            foil_list.append(spfr + "\n")
            foil_list.append(density + "\n")

            for measure in amount:
                foil_list.append(measure + "\n")

            foil_list.append("\n")

        # remove the unnecessary line break at the end of the list (now it matches the example file structure)
        foil_list.pop()

        # call for saving the detector foils
        try:
            with open(filepath + foilsname, "w") as file2:
                for item in foil_list:
                    file2.write(item)
        except IOError as e:
            print(e)

    def save_detector_params(self, detectorname, foilsname, filepath):
        """Writes the detector parameters into a file.

        Args:
            detectorname: Name of the file the parameters are written to.
            foilsname: Name of the file where the foil-specific parameters are.
            filepath: Path to the detector file.
        """
        detector = {"Detector type:": "TOF", "Detector angle:": "41.12", "Virtual detector size:": "2.0 5.0",
                    "Timing detector numbers:": "1 2", "Description file for the detector foils:": foilsname}
        foils = [
            {"Foil type:": "circular", "Foil diameter:": "7.0", "Foil distance:": "256.0"},
            {"Foil type:": "circular", "Foil diameter:": "9.0", "Foil distance:": "319.0"},
            {"Foil type:": "circular", "Foil diameter:": "18.0", "Foil distance:": "942.0"},
            {"Foil type:": "rectangular", "Foil size:": "14.0 14.0", "Foil distance:": "957.0"}
        ]

        separator1 = "=========="
        separator2 = "----------"

        detector_list = []
        for key, value in detector.items():
            detector_list.append(key + " " + value + "\n")

        detector_list.append(separator1 + "\n")

        for foil in foils:
            for key, value in foil.items():
                detector_list.append(key + " " + value + "\n")
            detector_list.append(separator2 + "\n")

        # remove the unnecessary line break and separator at the end of the list
        # (now it matches the example file structure)
        detector_list.pop()

        # save the detector parameters
        try:
            with open(filepath + detectorname, "w") as file1:
                for item in detector_list:
                    file1.write(item)
        except IOError as e:
            print(e)

    def save_target_params(self, targetname, filepath):
        """Writes the target parameters into a file.

        Args:
            targetname: Name of the file the parameters are written to.
            filepath: Path to the file.
        """
        target_elements = ["6.94 Li", "16.00 O", "28.09 Si", "54.94 Mn"]
        target_layers = [
            {"thickness": "0.01 nm", "stopping power for beam": "ZBL", "stopping power for recoil": "ZBL",
             "density": "0.000001 g/cm3", "amount": ["0 1.0"]},
            {"thickness": "90 nm", "stopping power for beam": "ZBL", "stopping power for recoil": "ZBL",
             "density": "4.0 g/cm3", "amount": ["0 0.048", "1 0.649", "3 0.303"]},
            {"thickness": "1000 nm", "stopping power for beam": "ZBL", "stopping power for recoil": "ZBL",
             "density": "2.32 g/cm3", "amount": ["2 1.0"]}
        ]

        # form the list that will be written to the file
        target_list = []
        for elem in target_elements:
            target_list.append(elem)
            target_list.append("\n")

        target_list.append("\n")

        for layer in target_layers:
            thickness = layer.get("thickness")
            spfb = layer.get("stopping power for beam")
            spfr = layer.get("stopping power for recoil")
            density = layer.get("density")
            amount = layer.get("amount")

            target_list.append(thickness + "\n")
            target_list.append(spfb + "\n")
            target_list.append(spfr + "\n")
            target_list.append(density + "\n")

            for measure in amount:
                target_list.append(measure + "\n")

            target_list.append("\n")

        # remove the unnecessary line break at the end of the list (now it matches the example file structure)
        target_list.pop()

        # call for saving target details
        try:
            with open(filepath + targetname, "w") as file3:
                for item in target_list:
                   file3.write(item)
        except IOError as e:
            print(e)

    def save_recoil_params(self, recoilname, filepath):
        """Writes the recoil parameters into a file.

        Args:
            recoilname: Name of the file the parameters are written to.
            filepath: Path to the file.
        """
        recoil_coordinates = [["0.00", "0.070"], ["95.00", "0.070"], ["95.01", "0.00001"], ["110.00", "0.00001"],
                              ["110.01", "0.00"], ["110.02", "0.00"]]
        recoil_list = []

        for pair in recoil_coordinates:
            x = pair[0]
            y = pair[1]
            recoil_list.append(x + " " + y + "\n")

        # call for saving recoiling distribution
        try:
            with open(filepath + recoilname, "w") as file4:
                for item in recoil_list:
                    file4.write(item)
        except IOError as e:
            print(e)

    def save_command_params(self, commandname, targetname, detectorname, recoilname, filepath):
        """Writes the command parameters into a file.

        Args:
            commandname: Name of the file the parameters are written to.
            targetname: Name of the file where the target-specific parameters are.
            detectorname: Name of the file where the detector-specific parameters are.
            recoilname: Name of the file where the recoil-specific parameters are.
            filepath: Path to the file.
        """
        header1 = "******************* Type of the simulation *******************************"
        header2 = "*************** General physical parameters for the simulation ***********"
        header3 = "********** Physical parameters conserning specific simulation type *********"
        subheader = "----------------------- ERD -simulation ------------------------------------"
        header4 = "******************* Parameters with physical significance ******************"
        header5 = "******************* Nonphysical parameters for simulation ***************"

        arguments1 = {"Type of simulation:": "ERD"}
        arguments2 = {"Beam ion": "35Cl", "Beam energy": "8.515 MeV"}
        arguments3 = {"Target description file:": targetname, "Detector description file:": detectorname,
                      "Recoiling atom:": "7Li", "Recoiling material distribution:": recoilname,
                      "Target angle:": "20.6 deg", "Beam spot size:": "0.5 3.0 nm"}
        arguments4 = {"Minimum angle of scattering:": "0.05 deg", "Minimum main scattering angle:": "20 deg",
                      "Minimum energy of ions:": "1.5 MeV", "Average number of recoils per primary ion:": "10",
                      "Recoil angle width (wide or narrow):": "narrow",
                      "Presimulation * result file:": "Cl-10-R2_O.pre", "Number of real ions per each scaling ion:": "5"
                      }
        arguments5 = {"Number of ions:": "1000000", "Number of ions in the presimulation:": "100000",
                      "Seed number of the random number generator:": "101"}

        argument_list = list()
        argument_list.append(header1 + "\n")
        arg_key, arg_value = list(arguments1.items())[0]
        argument_list.append(arg_key + " " + arg_value + "\n")

        argument_list.append(header2 + "\n")

        for key, value in arguments2.items():
            argument_list.append(key + " " + value + "\n")

        argument_list.append(header3 + "\n")
        argument_list.append(subheader + "\n")

        for key, value in arguments3.items():
            argument_list.append(key + " " + value + "\n")

        argument_list.append(header4 + "\n")
        for key, value in arguments4.items():
            argument_list.append(key + " " + value + "\n")

            argument_list.append(header5 + "\n")

            for key, value in arguments5.items():
                argument_list.append(key + " " + value + "\n")

            # call for saving the mcerd command
            try:
                with open(filepath + commandname, "w") as file5:
                    for item in argument_list:
                        file5.write(item)
            except IOError as e:
                print(e)

        def save_parameters(self, filepath=None):
            """Saves all the simulation parameters into their own files.

            Args:
                filepath: Path to the files.
            """
            # example filepath
            filepath = "C:\\MyTemp\\testikirjoitus\\"
            foilsname = "ilmaisinkerrokset.foils"
            detectorname = "ilmaisin.JyU"
            targetname = "kohtio.nayte"
            recoilname = "rekyyli.nayte_alkuaine"
            commandname = "sade-nayte_alkuaine"

            self.save_foil_params(foilsname, filepath)

            self.save_detector_params(detectorname, foilsname, filepath)

            self.save_target_params(targetname, filepath)

            self.save_recoil_params(recoilname, filepath)

            self.save_command_params(commandname, targetname, detectorname,
                                     recoilname, filepath)


