import hou
import os
import rbw_utils
import json

from PySide2 import QtCore, QtUiTools, QtWidgets, QtGui

from genshi.template.loader import directory
from jinja2.nodes import Break


class MyProject(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        scriptpath = hou.text.expandString("$RBW/ui/project_creator.ui")
        self.ui = QtUiTools.QUiLoader().load(scriptpath, parentWidget=self)
        self.setParent(hou.qt.mainWindow(), QtCore.Qt.Window)
        self.setWindowTitle("Project Creator")
        self.setMaximumSize(400, 500)

        # SET CONNECTIONS
        self.ui.int_validator = QtGui.QIntValidator()
        self.sel_directory = self.ui.findChild(QtWidgets.QPushButton, 'bt_directory')
        self.project_name = self.ui.findChild(QtWidgets.QLineEdit, 'le_proj_name')
        self.project_code = self.ui.findChild(QtWidgets.QLineEdit, 'le_proj')
        self.project_fps = self.ui.findChild(QtWidgets.QLineEdit, 'le_fps')
        self.project_folders = self.ui.findChild(QtWidgets.QPlainTextEdit, 'qpt_folders')
        self.create_project = self.ui.findChild(QtWidgets.QPushButton, 'bt_create_project')

        # SET VALUE
        self.project_name.setEnabled(False)
        self.project_code.setEnabled(False)
        self.project_fps.setEnabled(False)
        self.project_fps.setValidator(self.ui.int_validator)
        self.project_folders.setEnabled(False)
        self.create_project.setEnabled(False)

        self.sel_directory.clicked.connect(self.select_directory)
        self.create_project.clicked.connect(self.create_set_project)

    def select_directory(self):
        """
        Grabs the folder where to setup the new project
        """
        global directory
        start_directory = hou.text.expandString("$HOME")
        directory = hou.ui.selectFile(
            start_directory=start_directory,
            title="Select a folder where the project is going to be created",
            file_type=hou.fileType.Directory)

        rbw_utils.check_path_valid(directory)

        if directory:
            self.project_name.setEnabled(True)
            self.project_name.textChanged.connect(self.check_button_state)
            self.project_code.setEnabled(True)
            self.project_code.textChanged.connect(self.check_button_state)
            self.project_fps.setEnabled(True)
            self.project_fps.textChanged.connect(self.check_button_state)
            self.project_folders.setEnabled(True)

    def check_button_state(self):
        """
        Enable the Create Project Button only if the project code
        Project name and fps has text on it
        """

        if (self.project_name.text().strip()
            and self.project_code.text().strip()
            and self.project_fps.text().strip()
            and self.project_folders.toPlainText().strip()):
            self.create_project.setEnabled(True)
        else:
            self.create_project.setEnabled(False)

    def create_set_project(self):
        """
        Create the JSON file with the information provided by user.
        Grabs the path, name, code, fps and folders for a project.
        Saves it as JSON file.
        """
        # Defining the Variables
        project_name = self.project_name.text().strip()
        project_code = self.project_code.text().strip()
        project_fps = self.project_fps.text().strip()
        project_folders = [item_list.strip() for item_list in self.project_folders.toPlainText().split(",")]

        # new_list = []
        # temp_list = self.project_folders.toPlainText().split(",")
        #
        # for x in temp_list:
        #     clean = x.strip()
        #     new_list.append(clean)

        project_path = directory + project_name

        # Create the project dictionary
        project_dict = {
            project_name:{
                "PROJECT_CODE": project_code,
                "PROJECT_PATH": project_path,
                "PROJECT_FPS": project_fps,
                "PROJECT_FOLDERS": project_folders,
                "PROJECT_ACTIVE": False
            }
        }
        # JSON file path
        config_path = hou.text.expandString("$RBW/config")
        json_file_path = os.path.join(config_path, "project_config.json")

        if os.path.exists(json_file_path):
            with open(json_file_path, "r") as file:
                try:
                    data = json.load(file)
                except json.JSONDecodeError:
                    data = []
        else:
            data = []

        # Check for duplicate project name, code
        for existing_project in data:
            project_name_check = list(existing_project.keys())[0]
            project_data = existing_project[project_name_check]

            if (project_name_check == project_name
                    or existing_project[project_name_check]["PROJECT_CODE"] == project_code):
                hou.ui.displayMessage(
                    f"A project with the same name or code already exists:\n\n"
                    f"Name {project_name_check}\n"
                    f"Code {existing_project[project_name_check]['PROJECT_CODE']}\n"
                    f"Please choose a different name or code",
                    severity=hou.severityType.Error
                )
                return

        # Append new project data
        data.append(project_dict)

        # Save updated data back to the JSON file
        with open(json_file_path, "w") as file:
            json.dump(data, file, sort_keys=True, indent=4)

        print(f"Project data saved to {json_file_path}")

        # Create project folder and subfolders

        project_root = os.path.join(directory, project_name)
        os.makedirs(project_root, exist_ok=True)

        for folder in project_folders:
            folder_path = os.path.join(project_root, folder)
            os.makedirs(folder_path, exist_ok=True)

        print(f"Project folder structure created at {project_root}")
        hou.ui.displayMessage(f"Project {project_name} created successfully")



win = MyProject()
win.show()

# Ask for directory
# Check if is valid
# Request name, code, fps
# Request or not default folders
# create a Project
# Gather the information - dict
# Check if the JSON file exists - append
# if not create new file
# window = with the information that was saved