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

        # JSON file path
        self.config_path = hou.text.expandString("$RBW/config")
        self.json_path = os.path.join(self.config_path, "project_config.json")
        # print(self.json_path)