import hou

from PySide2 import QtWidgets, QtGui, QtCore


class TxToMtlx(QtWidgets.QMainWindow):

    def __init__(self):
        super().__init__()

        # SETUP CENTRAL WIDGET FOR UI
        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QtWidgets.QVBoxLayout(self.central_widget)

        # WINDOW PROPERTIES
        self.setWindowTitle("TexToMtlX Tool")
        self.resize(340, 570)
        self.setParent(hou.qt.mainWindow(), QtCore.Qt.Window)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)

        ## DATA
        self.mtlTX = False

        self._setup_help_section()
        self._setup_material_section()
        self._setup_list_section()
        self._setup_create_section()
        self._setup_connections()

    def _setup_help_section(self):
        '''Setup the help button section'''
        self.help_layout = QtWidgets.QVBoxLayout()

        self.bt_instructions = QtWidgets.QPushButton("Instructions")
        self.bt_instructions.setMinimumHeight(80)
        self.help_layout.addWidget(self.bt_instructions)
        self.main_layout.addLayout(self.help_layout)

    def _setup_material_section(self):
        '''Setup the material library section'''

        self.material_layout = QtWidgets.QGridLayout()
        # MATERIAL LIBRARY
        self.bt_lib = QtWidgets.QPushButton("Material Lib")
        self.bt_lib.setMinimumHeight(70)
        self.material_layout.addWidget(self.bt_lib, 0, 0, 2, 1)
        # TX CHECKBOX
        self.checkbox = QtWidgets.QCheckBox("Convert to TX?")
        self.checkbox.setEnabled(False)
        self.material_layout.addWidget(self.checkbox, 0, 1)
        # OPEN FOLDER
        self.bt_open_folder = QtWidgets.QPushButton("Open Folder")
        self.bt_open_folder.setMinimumHeight(40)
        self.bt_open_folder.setEnabled(False)
        self.material_layout.addWidget(self.bt_open_folder, 1, 1)

        self.main_layout.addLayout(self.material_layout)

    def _setup_list_section(self):
        '''Setup the material list section'''
        self.list_layout = QtWidgets.QVBoxLayout()

        # HEADER LAYOUT
        self.header_layout = QtWidgets.QHBoxLayout()

        self.lb_material_list = QtWidgets.QLabel("List of Materials:")
        self.bt_sel_all = QtWidgets.QPushButton("All")
        self.bt_sel_non = QtWidgets.QPushButton("Reset")

        self.bt_sel_all.setEnabled(False)
        self.bt_sel_non.setEnabled(False)

        self.header_layout.addWidget(self.lb_material_list)
        self.header_layout.addWidget(self.bt_sel_all)
        self.header_layout.addWidget(self.bt_sel_non)

        # MATERIAL LIST
        self.material_list = QtWidgets.QListView()
        self.material_list.setMinimumHeight(200)
        self.model = QtGui.QStandardItemModel()
        self.material_list.setModel(self.model)
        self.material_list.setSelectionMode(QtWidgets.QListView.MultiSelection)

        self.list_layout.addLayout(self.header_layout)
        self.list_layout.addWidget(self.material_list)
        self.main_layout.addLayout(self.list_layout)

    def _setup_create_section(self):
        """Setup the create button and progress bar section"""
        self.create_layout = QtWidgets.QVBoxLayout()

        # Create Button
        self.bt_create = QtWidgets.QPushButton("Create Materials")
        self.bt_create.setMinimumHeight(50)
        self.bt_create.setEnabled(False)

        # Progress Bar
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setMinimumHeight(30)
        self.progress_bar.setValue(0)

        self.create_layout.addWidget(self.bt_create)
        self.create_layout.addWidget(self.progress_bar)

        self.main_layout.addLayout(self.create_layout)

    def _setup_connections(self):
        '''Setup Signal Connections'''