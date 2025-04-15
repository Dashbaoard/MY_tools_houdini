import hou

from PySide2 import QtCore, QtWidgets
import glob

class SaveToolWindow(QtWidgets.QWidget):
    def __init__(self, project_data=None, scene_name=None, project_name=None):
        super().__init__()

        # Store project information
        self.project_data = project_data
        self.scene_name = scene_name
        self.project_name = project_name

        # Basic Window Setup
        self.setWindowTitle("Save Tool")
        self.resize(400, 200)
        self.setParent(hou.qt.mainWindow(), QtCore.Qt.Window)

        # Initialize the ui
        self._init_ui()
        self._setup_connections()
        self.update_project_info()

    def _init_ui(self):
        """ Initialize the UI components. """
        # Create the label
        self.project_info_label = QtWidgets.QLabel()
        self.project_info_label.setMaximumHeight(20)

        self.stage_label = QtWidgets.QLabel('STAGE')
        self.stage_label.setMaximumHeight(20)
        self.dept_label = QtWidgets.QLabel('DEPARTMENT')
        self.dept_label.setMaximumHeight(20)
        self.file_label = QtWidgets.QLabel('FILE NAME')
        self.file_label.setMaximumHeight(20)
        self.line_preview = QtWidgets.QLabel()
        self.line_preview.setMinimumHeight(30)

        # Create the combo boxes
        self.stage_combo = QtWidgets.QComboBox()
        self.stage_combo.setMinimumHeight(25)
        self.stage_combo.addItems(['MAIN', 'DEV', 'WIP'])

        self.dept_combo = QtWidgets.QComboBox()
        self.dept_combo.setMinimumHeight(25)
        self.dept_combo.addItems(['GEN', 'ANIM', 'CFX', 'ENV', 'FX', 'LRC', 'RIG', 'LAYOUT'])

        # Create text inputs
        self.file_name = QtWidgets.QLineEdit()
        self.file_name.setMinimumHeight(30)

        # Create the save button
        self.save_button = QtWidgets.QPushButton('SAVE')
        self.save_button.setMinimumSize(400, 50)

        # main layout
        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.addWidget(self.project_info_label)

        self.label_layout = QtWidgets.QHBoxLayout()
        self.combox_layout = QtWidgets.QHBoxLayout()

        # Assign layout to main
        self.main_layout.addLayout(self.label_layout)
        self.main_layout.addLayout(self.combox_layout)
        self.setLayout(self.main_layout)

        # Build the layout
        # self.main_layout.addWidget(self.project_info_label)
        self.label_layout.addWidget(self.stage_label)
        self.label_layout.addWidget(self.dept_label)
        self.combox_layout.addWidget(self.stage_combo)
        self.combox_layout.addWidget(self.dept_combo)
        self.main_layout.addWidget(self.file_label)
        self.main_layout.addWidget(self.file_name)
        self.main_layout.addWidget(self.save_button)
        self.main_layout.addWidget(self.line_preview)

    def _setup_connections(self):
        """ Setup the signal connections """

    def update_project_info(self):
        """ Update the project info label """
        if self.project_name and self.scene_name:
            info_text = f'{self.project_name} Ⅱ Scene {self.scene_name}'
        else:
            info_text = 'No project or scene selected.'

        self.project_info_label.setText(info_text)

    def update_preview_path(self):
        """ Update the preview path based on current selection"""
        if not self.project_name or not self.scene_name:
            self.line_preview.setText('Please select a project and a scene first')
            return

        stage = self.stage_combo.currentText()
        dept = self.dept_combo.currentText()
        file_name = self.file_name.text().replace(' ', '_') or 'unnamed'

        # Get project path
        project_path = self.project_data.get('PROJECT_PATH', '')

        # Get user and license information
        get_user = hou.getenv("USER")
        license_type = {
            "Commerrial": 'hip',
            'Indie': 'hiplc',
            'Apprentice': 'hipnc',
            'ApprenticeHD': 'hipnc',
            'Education': 'hipnc'
        }
        get_license = hou.licenseCategory().name()
        extension = license_type[get_license]

        # Create the path
        base_path = f'{project_path}/seq/{self.scene_name}/hip/{stage.lower()}_{dept.lower()}_{file_name.lower()}_{get_user.lower()}_{extension}'
        next_version = self.get_next_version(base_path)

    def get_next_version(self, base_path):
        """
        Find the next version number for the file
        Args:
            base_path (str): Base path without the version number and extension
        Returns:
            int: Next version number
        """
        license_type = {
            "Commerrial": 'hip',
            'Indie': 'hiplc',
            'Apprentice': 'hipnc',
            'ApprenticeHD': 'hipnc',
            'Education': 'hipnc'
        }
        get_license = hou.licenseCategory().name()
        extension = license_type[get_license]

        # Look for existings version
        pattern = f"{base_path}_v[0-9][0-9][0-9].{extension}"
        existing_files = glob.glob(pattern)

        if not existing_files:
            return 1

        versions = []

        for file in existing_files:
            try:
                #Extract version number from filename.
                version_str = file.split('_v')[-1].split('.')[0]
                version_num = int(version_str)
                versions.append(version_num)
            except(ValueError, IndexError):
                continue

        if not versions:
            return 1

# win = SaveToolWindow()
# win.show()
