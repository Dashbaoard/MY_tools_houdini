import hou
import os
import platform
import shutil
from datetime import datetime

from PySide2 import QtWidgets, QtCore, QtUiTools
# node = hou.pwd()

class SceneCacheManagerUI(QtWidgets.QWidget):
    # CONSTANT
    CACHE_NODES = {
        'filecache': 'file',
        'rop_geometry': 'sopoutput',
        'rop_alembic': 'filename',
        'rop_fbx': 'sopoutput',
        'rop_dop': 'dopoutput',
        'vellumio': 'sopoutput',
        'rbdio': 'sopoutput',
        'kinefx::characterio': 'sopoutput',

    }

    # Unit Conversion
    KB = 1024
    MB = 1024 * KB
    GB = 1024 * MB

    def __init__(self):
        super().__init__()
        scriptpath = hou.text.expandString("$RBW/ui/scene_cache_manager.ui")
        self.ui = QtUiTools.QUiLoader().load(scriptpath, parentWidget=self)
        self.setParent(hou.qt.mainWindow(), QtCore.Qt.Window)
        self.setWindowTitle("Scene Cache Manager")
        self.setMinimumWidth(1200)
        self._initUI()
        self._setup_connections()

        # STORE DATA
        self.cache_data = []

    def _initUI(self):
        """ Initialize the UI components. """
        self.cache_tree = self.ui.findChild(QtWidgets.QTreeWidget, 'cache_tree')
        self.total_nodes = self.ui.findChild(QtWidgets.QLabel, 'lb_total_nodes')
        self.total_cache = self.ui.findChild(QtWidgets.QLabel, 'lb_total_size')
        self.unused_version = self.ui.findChild(QtWidgets.QLabel, 'lb_unused_versions')
        self.scan_scene = self.ui.findChild(QtWidgets.QPushButton, 'bt_scan')
        self.show_explorer = self.ui.findChild(QtWidgets.QPushButton, 'bt_reveal')
        self.clean_old = self.ui.findChild(QtWidgets.QPushButton, 'bt_cleanup')

        # enable Alphabetic order
        self.cache_tree.setSortingEnabled(True)
        self.cache_tree.header().setSortIndicator(0, QtCore.Qt.AscendingOrder)

        # Add right-click context menu
        self.cache_tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.cache_tree.customContextMenuRequested.connect(self._show_context_menu)

    def _setup_connections(self):
        """ Set up signal connections."""
        self.scan_scene.clicked.connect(self.scan_scene_caches)
        self.cache_tree.itemDoubleClicked.connect(self.select_node)
        self.show_explorer.clicked.connect(self.reveal_in_explorer)
        self.clean_old.clicked.connect(self.cleanup_old_versions)

    def scan_scene_caches(self):
        """ Scan scene for all cache nodes and update UI"""
        try:
            self.cache_tree.clear()
            self.cache_data = []

            # Get all nodes in the scene

            for node_type, parm_name in self.CACHE_NODES.items():
                # Find all nodes based on the category
                for category in [hou.sopNodeTypeCategory(), hou.dopNodeTypeCategory(), hou.ropNodeTypeCategory()]:
                    node_type_sop = hou.nodeType(category, node_type)
                    if node_type_sop:
                        cache_nodes = node_type_sop.instances()

                        for node in cache_nodes:
                            cache_path = node.parm(parm_name).eval()
                            env_var = hou.text.expandString("$HIP")

                            if cache_path.startswith(env_var):
                                short_cache_path = cache_path.replace(env_var, '$HIP')
                            # Check if the path is valid
                            if not cache_path:
                                continue

                            node_name, node_path, node_type_name = self._get_node_details(node)
                            current_version = self._get_current_version(node_path)
                            node_data = {
                                'node_name': node_name,
                                'node_path': node_path,
                                'node_type': node_type_name,
                                'cache_path': cache_path,
                                'current_version': current_version,
                                'other_version': self._get_other_version(current_version, cache_path),
                                'last_modified': self._get_last_modified(cache_path),
                                'total_size': self.get_cache_size(cache_path, node.path())[0],
                                'size_unit': self.get_cache_size(cache_path, node.path())[1]
                            }

                            self._add_to_tree(node_data)
                            self.cache_data.append(node_data)

            self._update_stats()

        except Exception as e:
            hou.ui.displayMessage(f"Error scanning the scene:{str(e)})", severity=hou.severityType.Error)

    def _add_to_tree(self, node_data):
        """ Add a note entry to the tree widget."""
        item = QtWidgets.QTreeWidgetItem(self.cache_tree)
        item.setText(0, node_data['node_name'])
        item.setText(1, node_data['node_path'])
        item.setText(2, node_data['node_type'])
        item.setText(3, node_data['cache_path'])
        item.setText(4, str(node_data['current_version']))
        item.setText(5, str(node_data['other_version']))
        item.setText(6, node_data['last_modified'])
        item.setText(7, str(node_data['total_size']) + " " + node_data['size_unit'])
        # item.setText(7, str(node_data['total_size']))

    def _get_node_details(self, node):
        """
        Get the correct node details - name, path, type
        Args:
            node - the node we want to check
        Returns:
            tuple - with 3 value
        """
        node_name = node.name()
        node_path = node.path()
        node_type = node.type().name()
        check_parent = node.parent()

        if node_name == 'render' and check_parent.name() == 'filecache':
            node_name = node.parent().parent().name()
            node_path = node.parent().parent().path()
            node_type = node.parent().parent().type().name()
        elif node_name == 'render':
            node_name = node.parent().name()
            node_path = node.parent().path()
            node_type = node.parent().type().name()

        return node_name, node_path, node_type

    def _get_current_version(self, node_path):
        """
        Get the current version for filecache, ignores ROP nodes
        """
        node = hou.node(node_path)
        try:
            version = node.parm('version').eval()
            return version if version else "N/A"

        except AttributeError:
            return "N/A"

    def _get_other_version(self, current_version, cache_path):
        """ Get a list of version folders in the cache directory"""
        try:
            if current_version != "N/A":
                # Get the directory that contains the cache - root folder
                cache_dir = os.path.dirname(os.path.split(cache_path)[0])

                # Find all the version folders starting "v"
                version = []

                for item in os.listdir(cache_dir):
                    if os.path.isdir(os.path.join(cache_dir, item)) and item.startswith('v'):
                        try:
                            version_num = int(item[1:])
                            version.append(version_num)
                        except ValueError:
                            continue
                if len(version) == 0:
                    other_version = 0
                else:
                    other_version = len(version) - 1
                return other_version
            else:
                return '~'
        except OSError:
            return "N/A"

    def _get_last_modified(self, cache_path):
        """ Get the last modified date of a cache file"""
        try:
            timestamp = os.path.getmtime(cache_path)
            return datetime.fromtimestamp(timestamp).strftime('%d-%m-%Y - %H:%M')
        except(OSError,ValueError):
            return '~'

    def _show_context_menu(self, position):
        """Show context menu for right-click"""

        menu = QtWidgets.QMenu(self)
        selected_item = self.cache_tree.selectedItems()

        if selected_item:
            reveal_action = menu.addAction('Show Folder')
            reveal_action.triggered.connect(self.reveal_in_explorer)

            cleanup_action = menu.addAction('Clean old versions')
            cleanup_action.triggered.connect(self.cleanup_old_versions)

        menu.exec_(self.cache_tree.viewport().mapToGlobal(position))

    def _calculate_total_cache(self):
        """
        Calculates total size from self.cache_data - checks total_size and size_unit
        """
        multipliers = {
            "B": 1,
            "KB": 1024,
            "MB": 1024 ** 2,
            "GB": 1024 ** 3,
            "TB": 1024 ** 4,
        }

        total_bytes = 0

        # Loop through each item in the self.cache_data
        for item_data in self.cache_data:
            size = float(item_data['total_size'])
            unit = item_data['size_unit']

            # Convert to bytes
            bytes_to_convert = size * multipliers.get(unit, 1)
            total_bytes += bytes_to_convert

        # Convert total_bytes to the most appropriate unit
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        for unit in units:
            if total_bytes < 1024.0:
                return f'{total_bytes:.2f}', unit
            total_bytes /= 1024.0

        # If the size is larger than TB, return in TB
        return f'{total_bytes:.2f}', 'TB'

    def _update_stats(self):
        """Update the stats labs."""

        total_nodes = len(self.cache_data)
        self.total_nodes.setText(f"Total Cache Nodes: {total_nodes}")

        unused_version = sum(data['other_version'] for data in self.cache_data
                              if isinstance(data['other_version'], int))

        self.unused_version.setText(f"Unused Version: {unused_version}")
        total_bytes, size = self._calculate_total_cache()
        self.total_cache.setText(f'Total Cache Size: {total_bytes} {size}')


    def select_node(self, item):
        """Select a jump to the node when double-clicked"""
        node_path = item.text(1)
        node = hou.node(node_path)

        if node:
            # Select the node
            node.setSelected(True)
            # Finding the closest network editor pane
            for pane in hou.ui.paneTabs():
                if isinstance(pane, hou.NetworkEditor):
                    networkd_pane = pane
                    break

            if networkd_pane:
                # Move to the parent network
                networkd_pane.cd(node.parent().path())
                # Frame the node
                networkd_pane.frameSelection()
        else:
            node_delete = item.text(0)
            hou.ui.displayMessage(f"The node selected: {node_delete} isn't in the cache. Please refresh the Scene Cache Manager.",
                                  severity=hou.severity.Error)

    def reveal_in_explorer(self):
        """Open the folder where the current cache is saved"""
        selected_items = self.cache_tree.selectedItems()

        if not selected_items:
            hou.ui.displayMessage("Please select a cache first", severity=hou.severityType.Error)
            return

        cache_path = selected_items[0].text(3)
        dir_path = os.path.dirname(cache_path)

        if os.path.exists(dir_path):
            if platform.system() == 'Windows':
                os.startfile(dir_path)
            elif platform.system() == 'Darwin':
                os.system(f'open {dir_path}')
            else:
                os.system(f'xfg-open "{dir_path}')
        else:
            hou.ui.displayMessage(f"Directory not found: {dir_path}", severity=hou.severityType.Error)

    def get_cache_size(self, cache_path, node_path):
        """
        Calculates the total size of the cache directory adjusting the unit
        Args:
            cache_path = path to the cache directory
        Returns:
            tuple: Size and Unit - ie 1.5
        """
        try:
            node = hou.node(node_path)

            if not node:
                return 0,'B'

            parm = node.parm('trange')
            # frame_range = node.parm("trange").eval()
            if parm:
                frame_range = node.parm("trange").eval()
            else:
                # If 'trange' parameter does not exist, assume it's a single file cache
                frame_range = 0
            cache_folder = os.path.dirname(cache_path)
            if not os.path.exists(cache_folder):
                return 0,'B'

            # Check if is a single file
            if frame_range == 0:
                size = os.path.getsize(cache_path)
            else:
                # Check for directories
                size = 0
                for root, dir, files in os.walk(cache_folder):
                    for file in files:
                        file_path = os.path.join(root, file)
                        size += os.path.getsize(file_path)
            print(size)
            if size >= self.GB:
                return round(size / self.GB, 2), "GB"
            elif size >= self.MB:
                return round(size / self.MB, 2), "MB"
            elif size >= self.KB:
                return round(size / self.KB, 2), "KB"
            else:
                return size, "B"

        except Exception as e:
            hou.ui.displayMessage(f"Error calculating the cache size: {str(e)} + {node_path}", severity=hou.severityType.Error)
            return 0, "B"

    def cleanup_old_versions(self):
        """Clean up old versions of selected caches"""
        selected_items = self.cache_tree.selectedItems()

        if not selected_items:
            hou.ui.displayMessage("Please select a cache first", severity=hou.severityType.Error)
            return

        deletion_details = []
        total_size = 0

        for item in selected_items:
            current_version = item.text(4)
            if not current_version.isdigit():
                continue

            cache_path = item.text(3)
            root_folder = os.path.dirname(os.path.split(cache_path)[0])


            try:
                for folder in os.listdir(root_folder):
                    folder_path = os.path.join(root_folder, folder)

                    if (os.path.isdir(folder_path) and
                            folder.startswith('v') and
                            folder != f"v{current_version}"):
                        size, unit = self.get_cache_size(folder_path, item.text(1))
                        total_size += size

                        deletion_details.append(
                            f'Node: {item.text(0)}\n'
                            f' - Version: {folder}\n'
                            f' - Size: {size} {unit}\n'
                            f' - Path: {folder_path}'
                        )
            except UnboundLocalError as e:
                hou.ui.displayMessage(
                    f'Error accessing folder {root_folder}: {str(e)}',
                    severity=hou.severityType.Error
                )


        if not deletion_details:
            hou.ui.displayMessage(
                f'No old versions found to clean up for : {item.text(0)}',
                severity=hou.severityType.Message)
            return

        message = (f'The following {len(selected_items)} versions will be deleted:\n\n' +
                   "\n".join(deletion_details) +
                   "\n Are you sure you want to proceed?")

        get_confirmation = hou.ui.displayMessage(
            message,
            buttons=('Yes', 'No!!!'),
            severity=hou.severityType.Warning,
            close_choice=1
        )


        if get_confirmation == 0:
            try:
                for item in selected_items:
                    check_version = item.text(4)
                    node_path = item.text(3)
                    root_folder = os.path.dirname(os.path.split(node_path)[0])

                for root, dir, _ in os.walk(root_folder):
                    for folder in dir:
                        if folder != f"v{check_version}":
                            folder_to_delete = os.path.join(root, folder)

                            if os.path.exists(folder_to_delete):
                                shutil.rmtree(folder_to_delete)

                self.scan_scene_caches()
                hou.ui.displayMessage("Cleanup completed", severity=hou.severityType.Message)
            except OSError as e:
                hou.ui.displayMessage(f'Error during cleanup: {str(e)}', severity=hou.severityType.Error)



