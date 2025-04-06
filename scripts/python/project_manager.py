import hou
import os
import rbw_utils
import json
import shutil
import pdb

from PySide2 import QtCore, QtUiTools, QtWidgets, QtGui

from genshi.template.loader import directory
from jinja2.nodes import Break


class MyProject(QtWidgets.QMainWindow):
    # class constant
    CONFIG_DIR = "$RBW/config"
    CONFIG_FILE = "project_config.json"
    UI_FILE = "$RBW/ui/project_manager.ui"

    def __init__(self):
        super().__init__()

        # INITIALIZE UI
        self._init_ui()
        self._setup_connections()
        # STORE PROJECT DATA
        self.project_data = []

        # LOAD PROJECTS WHEN INITIALIZING
        self.load_projects()

    def _init_ui(self):
        """
        Initialize the UI Connections.
        """
        scriptpath = hou.text.expandString(self.UI_FILE)
        self.ui = QtUiTools.QUiLoader().load(scriptpath, parentWidget=self)
        self.setParent(hou.qt.mainWindow(), QtCore.Qt.Window)
        self.setWindowTitle("Project Creator")
        self.setMaximumSize(600, 400)

        # SET CONNECTIONS
        self.project_list = self.ui.findChild(QtWidgets.QListWidget, "lw_projects")

        self.details_button = self.ui.findChild(QtWidgets.QPushButton, "bt_proj_details")
        self.enable_button = self.ui.findChild(QtWidgets.QPushButton, "bt_proj_enable")
        self.disable_button = self.ui.findChild(QtWidgets.QPushButton, "bt_proj_disable")
        self.delete_button = self.ui.findChild(QtWidgets.QPushButton, "bt_proj_delete")
        # SEQUENCES
        self.sequence_list = self.ui.findChild(QtWidgets.QListWidget, "lw_seq")
        self.create_scene = self.ui.findChild(QtWidgets.QPushButton, "create_scene")
        self.delete_scene = self.ui.findChild(QtWidgets.QPushButton, "delete_scene")
        # FILES
        self.files_list = self.ui.findChild(QtWidgets.QListWidget, "lw_files")
        self.open_file = self.ui.findChild(QtWidgets.QPushButton, "bt_open")
        self.save_file = self.ui.findChild(QtWidgets.QPushButton, "bt_save")
        self.status_line = self.ui.findChild(QtWidgets.QLineEdit, "lineEdit")

    def _setup_connections(self):
        """
        Setup the signal connections.
        """
        # SET VALUES
        self.details_button.clicked.connect(self.show_project_details)

        self.enable_button.clicked.connect(lambda : self.toggle_project(True))
        self.disable_button.clicked.connect(lambda : self.toggle_project(False))
        self.delete_button.clicked.connect(self.remove_project)
        self.project_list.currentItemChanged.connect(self.handle_item_change)

        self.sequence_list.itemSelectionChanged.connect(self.load_files)

        self.create_scene.clicked.connect(self.create_project_folder)
        self.delete_scene.clicked.connect(self.delete_project_folder)
        self.open_file.clicked.connect(self.open_project_file)
        self.save_file.clicked.connect(self.save_project_file)

    def handle_item_change(self, current, previous):
        """
        Only call load_scenes when there is a valid current item
        Args:
            current: The current QListWidgetItem
            previous: The previous QListWidgetItem
        """
        if current is not None:
            self.load_scenes()

    def update_status(self, message, severity=None):
        """
        Update status line and optionally display message
        Args:
             message (str): message to display
             severity (hou.severityType, optional): severity for UI display.
        """
        self.status_line.setText(message)
        if severity is not None:
            hou.ui.displayMessage(message, severity=severity)

    def get_selected_projects(self):
        """
        Get currently selected project or display error
        Returns:
             tuple: (project_name, project_data) or (None, None) if no selection
        """
        if not self.project_list.selectedItems(): # Checks if a project is selected first
            self.update_status("Please select a project11", hou.severityType.Error)
            return None, None
        project_name = self.project_list.currentItem().text()
        project_data = None
        for project in self.project_data:
            if project_name in project:
                project_data = project[project_name]
                break

        return project_name, project_data

    def load_projects(self):
        """
        Load project from JSON file and populate the project list.
        """
        try:
            path = hou.text.expandString("$RBW/config")
            json_path = os.path.join(path, "project_config.json")

            with open(json_path, "r") as file:
                self.project_data = json.load(file)

            project_names = []

            for project in self.project_data:
                project_name = list(project.keys())[0]
                project_names.append(project_name)

            self.project_list.clear()
            project_names.sort()

            # add sorted project names to the list widget
            for name in project_names:
                self.project_list.addItem(name)

            self.status_line.setText(f"{json_path}was loaded")

        except Exception as e:
            self.status_line.setText("No project was found")

    def show_project_details(self):
        """
        Display project details in a message box.
        """

        project_name, project_data = self.get_selected_projects()

        if not project_name:
            return

        if project_data:
            hou.ui.displayMessage(
                f"Project Details for {project_name}:\n"
                f"Project code: {project_data['PROJECT_CODE']}\n"
                f"Project path: {project_data['PROJECT_PATH']}\n"
                f"project FPS: {project_data['PROJECT_FPS']}",
                title = f"Details for {project_name}")
        else:
            hou.ui.displayMessage(f"Project '{project_name}' not found")

    def toggle_project(self, status=True):
        """
        Toggle the project env variables.
        Args:
            status (bool): Toggle to enable, False to disable.
        """

        project_name, project_data = self.get_selected_projects()

        env_vars = {"JOB":"", "CODE":"", "FPS":"", "PROJECT":"" }
        project_name = self.project_list.currentItem().text()

        if status:
            if project_data:
                env_vars.update(
                    {
                        "JOB":project_data['PROJECT_PATH'],
                        "CODE":project_data['PROJECT_CODE'],
                        "FPS":project_data['PROJECT_FPS'],
                        "PROJECT":project_name
                    }
                )
                status_msg = f"Current active project is: {project_name}"
            else:
                self.update_status(f"Could not find data for project {project_name}.",
                                      hou.severityType.Error)
                return

        else:
            status_msg = f"Project '{project_name}' is disabled."

        for var, value in env_vars.items():
            hou.putenv(var, value)

        # Update the status line
        self.update_status(status_msg, hou.severityType.Error)

    def remove_project(self):
        """
        Remove the selected project from the JSON file, the list widget and deletes the folder.
        """
        if not self.project_list.selectedItems():
            self.update_status("Please select a project.", hou.severityType.Error)
            return
        current_item = self.project_list.currentItem().text()

        # Confirmation from the user

        confirm_delete = hou.ui.displayMessage(
            f"Are you sure you want to delete {current_item}?\n"
            f"ATTENTION!!! - This action will delete all the folders and file for project!",
            buttons=('Yes', 'No'),
            severity=hou.severityType.Warning,
            close_choice=1
        )
        if confirm_delete == 1:
            return

        try:
            path = hou.text.expandString("$RBW/config")
            json_path = os.path.join(path, "project_config.json")

            with open(json_path, "r") as file:
                self.projects_data = json.load(file)

            project_path_delete = None

            for project in self.projects_data:
                if current_item in project:

                    project_data = project[current_item]
                    project_path_delete = project_data['PROJECT_PATH']
                    self.project_data.remove(project)
                    break

            if project_path_delete:
                if os.path.exists(project_path_delete):
                    try:
                        shutil.rmtree(project_path_delete)
                    except Exception as e:
                        self.update_status(f"Error deleting project directory : {str(e)}", hou.severityType.Error)

            with open(json_path, "w") as file:
                json.dump(self.project_data, file, sort_keys=True, indent=4)

            self.load_projects()

            self.update_status(f"Project {current_item} has been deleted.", hou.severityType.Message)


        except Exception as e:
            self.update_status(f"Error during project deletion: {str(e)}")

    def load_scenes(self):
        """
        This loads the folders inside the SEQ folder for each project
        """

        current_item = self.project_list.currentItem().text()

        try:
            self.sequence_list.clear()
            for project in self.project_data:
                if current_item in project:
                    project_data = project[current_item]
                    seq_path = os.path.join(project_data['PROJECT_PATH'], "seq").replace(os.sep, "/")
                    print(seq_path)
                    if os.path.exists(seq_path):
                        sequences = []

                        for dir in os.listdir(seq_path):
                            if os.path.isdir(os.path.join(seq_path, dir)):
                                sequences.append(dir)

                        sequences.sort()

                        for scene in sequences:
                            self.sequence_list.addItem(scene)
                    else:
                        error_msg = f"No sequence folder found for the project {current_item}."
                        self.status_line.setText(error_msg)
                    break

        except Exception as e:
            error_msg = f"Error loading sequence: {str(e)}"
            hou.ui.displayMessage(error_msg, severity=hou.severityType.Error)
            self.status_line.setText(error_msg)

    def create_project_folder(self):
        """
        Create a new project folder based on the selected project and sequence.
        """
        if not self.project_list.selectedItems():
            self.update_status("Please select a project.", hou.severityType.Error)
            return
        current_item = self.project_list.currentItem().text()


        for project in self.project_data:
            if current_item in project:
                project_data = project[current_item]
                seq_path = os.path.join(project_data['PROJECT_PATH'], "seq").replace(os.sep, "/")

        if not os.path.exists(seq_path):
            self.update_status(f"Project path not found for {seq_path}.", hou.severityType.Error)
            return
        else:
            folder_name, ok = QtWidgets.QInputDialog.getText(self, "Create Folder", "Enter folder name:")
            if not ok or not folder_name:
                self.status_line.setText("Folder creation cancelled.")
                return
            folder_path = os.path.join(seq_path, folder_name).replace(os.sep, "/")
            if os.path.exists(folder_path):
                self.update_status(f"Folder already exists: {folder_path}", hou.severityType.Warning)
                return

            try:
                os.makedirs(folder_path)
                self.update_status(f"Created folder: {folder_path}", hou.severityType.Message)
                self.load_scenes()

            except Exception as e:
                self.update_status(f"Error creating folder: {str(e)}", hou.severityType.Error)

    def delete_project_folder(self):
        """
        Delete the selected project folder.
        """
        # Check if a sequence is selected
        if not self.sequence_list.selectedItems():
            self.update_status("Please select a sequence.",hou.severityType.Error)
            return

        # Get the current project and sequence
        current_project = self.project_list.currentItem().text()
        current_sequence = self.sequence_list.currentItem().text()

        # Find the project data
        for project in self.project_data:
            if current_project in project:
                project_data = project[current_project]
                break

        # Define the scene path
        scene_path = os.path.join(project_data['PROJECT_PATH'], "seq", current_sequence).replace(os.sep, "/")

        # Check if the scene path exists
        if not os.path.exists(scene_path):
            hou.ui.displayMessage(f"Scene path not found: {scene_path}", severity=hou.severityType.Error)
            self.status_line.setText(f"Scene path not found: {scene_path}")
            return

        # Confirm deletion
        confirm_delete = hou.ui.displayMessage(
            f"Are you sure you want to delete {current_sequence}?\n"
            f"ATTENTION!!! - This action will delete all the files in the folder!",
            buttons=('Yes', 'No'),
            severity=hou.severityType.Warning,
            close_choice=1
        )
        if confirm_delete == 1:  # User clicked 'No'
            return

        try:
            shutil.rmtree(scene_path)
            self.status_line.setText(f"Deleted folder: {scene_path}")
            hou.ui.displayMessage(f"Deleted folder: {scene_path}", severity=hou.severityType.Message)

            # Update the scenes list
            self.load_scenes()

        except Exception as e:
            error_msg = f"Error deleting folder: {str(e)}"
            hou.ui.displayMessage(error_msg, severity=hou.severityType.Error)
            self.status_line.setText(error_msg)

    def load_files(self):
        """
        This loads the files inside the selected sequence folder for each project.
        """
        # Get the current project and sequence
        current_project = self.project_list.currentItem().text()
        current_sequence = self.sequence_list.currentItem().text()

        try:
            self.files_list.clear()
            for project in self.project_data:
                if current_project in project:
                    project_data = project[current_project]
                    seq_path = os.path.join(project_data['PROJECT_PATH'], "seq", current_sequence).replace(os.sep, "/")
                    if os.path.exists(seq_path):
                        files = []

                        for file in os.listdir(seq_path):
                            if os.path.isfile(os.path.join(seq_path, file)):
                                files.append(file)

                        files.sort()

                        for file in files:
                            self.files_list.addItem(file)
                    else:
                        error_msg = f"No sequence folder found for the project {current_project} and sequence {current_sequence}."
                        self.status_line.setText(error_msg)
                    break

        except Exception as e:
            error_msg = f"Error loading files: {str(e)}"
            # hou.ui.displayMessage(error_msg, severity=hou.severityType.Error)
            self.status_line.setText(error_msg)

    def save_project_file(self):
        """
        Save the project file to the selected project and sequence folder.
        """

        if not self.sequence_list.selectedItems():
            hou.ui.displayMessage("Please select a sequence.", severity=hou.severityType.Error)
            self.status_line.setText("Please select a sequence.")
            return

        current_project = self.project_list.currentItem().text()
        current_sequence = self.sequence_list.currentItem().text()

        for project in self.project_data:
            if current_project in project:
                project_data = project[current_project]

                break
        save_path = os.path.join(project_data['PROJECT_PATH'], "seq", current_sequence).replace(os.sep, "/")


        # Prompt user to select a file name
        file_name, ok = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save Project File",
            save_path,
            "Houdini Files (*.hip *.hipnc)"
        )
        if not ok or not file_name:
            self.status_line.setText("File save cancelled.")
            return

        # Save the file
        try:
            hou.hipFile.save(file_name)
            self.status_line.setText(f"File saved: {file_name}")
            hou.ui.displayMessage(f"File saved: {file_name}", severity=hou.severityType.Message)
            self.load_files()
        except Exception as e:
            error_msg = f"Error saving file: {str(e)}"
            hou.ui.displayMessage(error_msg, severity=hou.severityType.Error)
            self.status_line.setText(error_msg)




    def open_project_file(self):
        """
        Open the selected project file.
        """
        current_project = self.project_list.currentItem().text()
        current_sequence = self.sequence_list.currentItem().text()
        selected_file = self.files_list.currentItem().text()

        for project in self.project_data:
            if current_project in project:
                project_data = project[current_project]
                project_path = project_data['PROJECT_PATH']
                break

        file_path = os.path.join(project_path, "seq", current_sequence, selected_file).replace(os.sep, "/")

        try:
            hou.hipFile.load(file_path)
            self.status_line.setText(f"File opened: {file_path}")
            # hou.ui.displayMessage(f"File opened: {file_path}", severity=hou.severityType.Message)
        except Exception as e:
            self.update_status(f"Error opening file: {str(e)}", hou.severityType.Error)


win = MyProject()
win.show()

