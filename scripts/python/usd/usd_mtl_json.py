# _*_ coding: utf-8 _*_
# .@FileName:usd_mtl_json
# .@Date....:2025-06-22 : 21 : 32
# .@Aurhor..:冥羽
# .@Contact.:1942598111@qq.com
'''
launch:
        import usd_mtl_json as Qs_FileName
        reload(FileName)
        FileName.main()
'''
import os
import re
import json
import hou
import pprint
import subprocess
import time
import logging
import threading
import traceback

from PySide2 import QtWidgets, QtGui, QtCore
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed


class JsonToMtlx(QtWidgets.QMainWindow):

    def __init__(self):
        super().__init__()

        # SETUP CENTRAL WIDGET FOR UI
        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QtWidgets.QVBoxLayout(self.central_widget)

        # WINDOW PROPERTIES
        self.setWindowTitle("Arnold to MaterialX Converter")
        self.resize(340, 570)
        self.setParent(hou.qt.mainWindow(), QtCore.Qt.Window)
        self.setWindowFlags(self.windowFlags())

        # DATA
        self.json_data = None
        self.material_nodes = {}
        self.texture_nodes = {}
        self.connections = {}
        self.assigned_objects = {}
        self.node_lib = None  # 初始化节点库
        self.node_path = None  # 存储节点路径

        self._setup_help_section()
        self._setup_material_section()
        self._setup_list_section()
        self._setup_create_section()
        self._setup_connections()
        self.init_constants()

    def init_constants(self):
        """Initializing constants values used throughout the class."""
        # MaterialX node mapping for Arnold parameters
        self.ARNOLD_TO_MTLX_MAPPING = {
            "baseColor": "base_color",
            "specularColor": "specular_color",
            "metalness": "metalness",
            "specularRoughness": "specular_roughness",
            "emissionColor": "emission_color",
            "opacity": "opacity",
            "normalCamera": "normal",
            "coatColor": "coat_color",
            "coatRoughness": "coat_roughness",
            "transmissionColor": "transmission_color",
            "subsurfaceColor": "subsurface_color",
            "sheenColor": "sheen_color",
            "sheenRoughness": "sheen_roughness"
        }

        # Arnold node types to MaterialX conversion
        self.ARNOLD_NODE_MAPPING = {
            "aiStandardSurface": "mtlxstandard_surface",
            "aiImage": "mtlximage",
            "aiColorCorrect": "mtlxramp_rgb",
            "aiNormalMap": "mtlxnormalmap",
            "aiBump2d": "mtlxbump",
            "aiRange": "mtlxrange",
            "aiAdd": "mtlxadd",
            "aiMultiply": "mtlxmultiply"
        }

    def _setup_help_section(self):
        ''' Setup the help button section'''
        self.help_layout = QtWidgets.QVBoxLayout()

        self.bt_instructions = QtWidgets.QPushButton("Instructions")
        self.bt_instructions.setMinimumHeight(40)
        self.help_layout.addWidget(self.bt_instructions)
        self.main_layout.addLayout(self.help_layout)

    def _setup_material_section(self):
        '''Setup the material library section'''
        self.material_layout = QtWidgets.QGridLayout()

        # MATERIAL LIBRARY
        self.bt_lib = QtWidgets.QPushButton("Material Lib")
        self.bt_lib.setMinimumHeight(40)
        self.material_layout.addWidget(self.bt_lib, 0, 0)

        # OPEN JSON
        self.bt_open_json = QtWidgets.QPushButton("Open JSON")
        self.bt_open_json.setMinimumHeight(40)
        self.bt_open_json.setEnabled(False)  # 默认禁用，直到选择材质库
        self.material_layout.addWidget(self.bt_open_json, 0, 1)

        self.main_layout.addLayout(self.material_layout)

    def _setup_list_section(self):
        '''Setup the material list section'''
        self.list_layout = QtWidgets.QVBoxLayout()

        # HEADER LAYOUT
        self.header_layout = QtWidgets.QHBoxLayout()

        self.lb_material_list = QtWidgets.QLabel("Materials in JSON:")
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
        self.bt_instructions.clicked.connect(self.help_menu)
        self.bt_lib.clicked.connect(self.get_mtl_lib)
        self.bt_open_json.clicked.connect(self.open_json_file)
        self.bt_sel_all.clicked.connect(self.select_all_mtl)
        self.bt_sel_non.clicked.connect(self.deselect_all_mtl)
        self.bt_create.clicked.connect(self.create_materials)

    def help_menu(self):
        """ Simple method to show instructions on how to use the tool."""
        text_to_display = """
        Arnold to MaterialX Converter

        Instructions:
        1. Select a material library node in Houdini
        2. Open a JSON file containing Arnold material definitions
        3. Select materials to convert from the list
        4. Click "Create Materials" to generate MaterialX networks

        The tool will:
        - Convert Arnold aiStandardSurface to MaterialX Standard Surface
        - Convert Arnold image nodes to MaterialX image nodes
        - Recreate node connections and networks
        - Apply materials to assigned objects (if available)
        """
        hou.ui.displayMessage(text_to_display, severity=hou.severityType.ImportantMessage)

    def get_mtl_lib(self):
        """ Get the base material library where the materials are going to saved"""
        selected_path = hou.ui.selectNode(
            title="Please select a material library",
            node_type_filter=hou.nodeTypeFilter.ShopMaterial)

        if selected_path:
            # 存储节点路径而不是节点对象
            self.node_path = selected_path
            self.bt_open_json.setEnabled(True)

    def open_json_file(self):
        """Open and parse JSON material file"""
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open JSON File", "", "JSON Files (*.json)"
        )

        if not file_path:
            return

        try:
            with open(file_path, 'r') as f:
                self.json_data = json.load(f)

            # Extract material nodes
            self.material_nodes = {}
            self.texture_nodes = {}
            self.connections = {}
            self.assigned_objects = {}

            for node_name, node_data in self.json_data.items():
                node_type = node_data.get("type", "")

                if "aiStandardSurface" in node_type:
                    self.material_nodes[node_name] = node_data
                    # Store assigned objects
                    self.assigned_objects[node_name] = node_data.get("assigned_to", [])
                elif "aiImage" in node_type:
                    self.texture_nodes[node_name] = node_data

                # Store connections
                if "connections" in node_data:
                    self.connections[node_name] = node_data["connections"]

            # Update UI with material names
            self.model.clear()
            for mat_name in self.material_nodes.keys():
                self.model.appendRow(QtGui.QStandardItem(mat_name))

            self.bt_sel_all.setEnabled(True)
            self.bt_sel_non.setEnabled(True)
            self.bt_create.setEnabled(True)

        except Exception as e:
            hou.ui.displayMessage(f"Error loading JSON: {str(e)}", severity=hou.severityType.Error)
            traceback.print_exc()

    def select_all_mtl(self):
        """Select all the items in the list view."""
        selection_node1 = self.material_list.selectionModel()
        for row in range(self.model.rowCount()):
            index = self.model.index(row, 0)
            selection_node1.select(index, QtCore.QItemSelectionModel.Select)

    def deselect_all_mtl(self):
        """Clear all selections in the list view."""
        self.material_list.clearSelection()

    def create_materials(self):
        """Convert selected Arnold materials to MaterialX"""
        selected_rows = self.material_list.selectedIndexes()

        if len(selected_rows) == 0:
            hou.ui.displayMessage(
                "Please select at least one material.",
                severity=hou.severityType.Error
            )
            return

        if not self.node_path:
            hou.ui.displayMessage(
                "Please select a material library first.",
                severity=hou.severityType.Error
            )
            return

        # 每次操作前重新获取节点
        node_lib = hou.node(self.node_path)
        if not node_lib:
            hou.ui.displayMessage(
                "Material library no longer exists. Please select a new one.",
                severity=hou.severityType.Error
            )
            return

        # Setup progress bar
        self.progress_bar.setMaximum(len(selected_rows))
        progress_count = 0

        # Convert each selected material
        for index in selected_rows:
            material_name = index.data()
            if material_name in self.material_nodes:
                try:
                    creator = ArnoldToMtlxConverter(
                        material_name,
                        self.material_nodes[material_name],
                        self.node_path,  # 传递节点路径而不是节点对象
                        self.json_data
                    )
                    mtlx_node = creator.convert()

                    # Assign material to objects if available
                    if material_name in self.assigned_objects and mtlx_node:
                        self.assign_material_to_objects(material_name, mtlx_node)

                except Exception as e:
                    hou.ui.displayMessage(
                        f"Error converting {material_name}: {str(e)}",
                        severity=hou.severityType.Error
                    )
                    traceback.print_exc()

            progress_count += 1
            self.progress_bar.setValue(progress_count)

        hou.ui.displayMessage("Material conversion completed!", severity=hou.severityType.Message)

    def assign_material_to_objects(self, material_name, mtlx_node):
        """Assign created material to objects specified in JSON"""
        if not mtlx_node:
            return

        objects = self.assigned_objects.get(material_name, [])
        if not objects:
            return

        # Get /obj context
        obj_context = hou.node("/obj")
        if not obj_context:
            return

        # Apply material to each object
        for obj_name in objects:
            obj_node = obj_context.node(obj_name)
            if obj_node:
                # Get geometry node
                geo_node = None
                for child in obj_node.children():
                    if child.type().name() == "geo":
                        geo_node = child
                        break

                if geo_node:
                    # Assign material
                    shop_material_path = mtlx_node.path()
                    geo_node.parm("shop_materialpath").set(shop_material_path)


class ArnoldToMtlxConverter:
    def __init__(self, material_name, material_data, material_lib_path, json_data):
        self.material_name = material_name
        self.material_data = material_data
        self.material_lib_path = material_lib_path
        self.json_data = json_data
        self.created_nodes = {}
        self.mtlx_node = None  # 存储创建的MaterialX节点

        # 映射定义
        self.ARNOLD_TO_MTLX_MAPPING = {
            "base": "base",
            "baseColor": "base_color",
            "diffuseRoughness": "diffuse_roughness",
            "metalness": "metalness",
            "specular": "specular",
            "specularColor": "specular_color",
            "specularRoughness": "specular_roughness",
            "specularIOR": "specular_IOR",
            "specularAnisotropy": "specular_anisotropy",
            "specularRotation": "specular_rotation",
            "transmission": "transmission",
            "transmissionColor": "transmission_color",
            "transmissionDepth": "transmission_depth",
            "transmissionScatter": "transmission_scatter",
            "transmissionScatterAnisotropy": "transmission_scatter_anisotropy",
            "transmissionDispersion": "transmission_dispersion",
            "transmissionExtraRoughness": "transmission_extra_roughness",
            "subsurface": "subsurface",
            "subsurfaceColor": "subsurface_color",
            "subsurfaceRadius": "subsurface_radius",
            "subsurfaceScale": "subsurface_scale",
            "subsurfaceType": "subsurface_type",
            "subsurfaceAnisotropy": "subsurface_anisotropy",
            "coat": "coat",
            "coatColor": "coat_color",
            "coatRoughness": "coat_roughness",
            "coatIOR": "coat_IOR",
            "coatAnisotropy": "coat_anisotropy",
            "coatRotation": "coat_rotation",
            "sheen": "sheen",
            "sheenColor": "sheen_color",
            "sheenRoughness": "sheen_roughness",
            "emission": "emission",
            "emissionColor": "emission_color",
            "opacity": "opacity",
            "normalCamera": "normal"
        }

        self.ARNOLD_NODE_MAPPING = {
            "aiStandardSurface": "mtlxstandard_surface",
            "aiImage": "mtlximage",
            "aiColorCorrect": "mtlxramp_rgb",
            "aiNormalMap": "mtlxnormalmap",
            "aiBump2d": "mtlxbump",
            "aiRange": "mtlxrange",
            "aiAdd": "mtlxadd",
            "aiMultiply": "mtlxmultiply"
        }

    def convert(self):
        """Main conversion method"""
        try:
            # 获取材质库节点
            material_lib = hou.node(self.material_lib_path)
            if not material_lib:
                raise RuntimeError(f"Material library node not found: {self.material_lib_path}")

            # Create material subnet
            material_subnet = self._create_material_subnet(material_lib)
            self.mtlx_node = material_subnet  # 存储创建的节点

            # Create standard surface node
            std_surface = material_subnet.createNode("mtlxstandard_surface", f"{self.material_name}_surf")
            self.created_nodes[self.material_name] = std_surface

            # Set base parameters
            self._set_base_parameters(std_surface)

            # Process connections
            self._process_connections(material_lib)

            # Create output nodes
            self._create_output_nodes(material_subnet, std_surface)

            # Layout nodes
            material_subnet.layoutChildren()

            # 返回创建的节点
            return material_subnet

        except Exception as e:
            hou.ui.displayMessage(f"Error converting material {self.material_name}: {str(e)}",
                                  severity=hou.severityType.Error)
            traceback.print_exc()
            return None

    def _create_material_subnet(self, material_lib):
        """Create subnet for the material"""
        # 安全删除现有材质
        existing_material = material_lib.node(self.material_name)
        if existing_material:
            try:
                # 尝试删除现有节点
                existing_material.destroy()
            except hou.ObjectWasDeleted:
                # 节点已被删除，无需处理
                pass
            except Exception as e:
                print(f"Warning: Could not delete existing material: {str(e)}")

        # 创建新材质节点
        mtlx_subnet = material_lib.createNode('subnet', self.material_name)

        # 删除默认子节点
        for child in mtlx_subnet.children():
            try:
                child.destroy()
            except hou.ObjectWasDeleted:
                # 节点已被删除，跳过
                pass
            except Exception as e:
                print(f"Warning: Could not delete child node: {str(e)}")

        # 设置材质参数
        self._setup_material_parameters(mtlx_subnet)
        mtlx_subnet.setMaterialFlag(True)

        return mtlx_subnet

    def _setup_material_parameters(self, subnet):
        """Setup USD materialX Builder Subnet parameters"""
        # 创建参数模板组
        parm_template_group = subnet.parmTemplateGroup()

        # MaterialX文件夹
        folder = hou.FolderParmTemplate("folder1", "MaterialX Builder",
                                        folder_type=hou.folderType.Collapsible)

        # 继承控制
        inherit_ctrl = hou.IntParmTemplate("inherit_ctrl", "Inherit from Class", 1,
                                           menu_items=["0", "1", "2"],
                                           menu_labels=["Never", "Always", "Material Flag"],
                                           default_value=([2]))
        folder.addParmTemplate(inherit_ctrl)

        # 类弧
        shader_ref = hou.StringParmTemplate("shader_referencetype", "Class Arc", 1,
                                            default_value=([
                                                "n = hou.pwd()\nn_hasFlag = n.isMaterialFlagSet()\ni = n.evalParm('inherit_ctrl')\nr = 'none'\nif i == 1 or (n_hasFlag and i == 2):\n    r = 'inherit'\nreturn r"]))
        folder.addParmTemplate(shader_ref)

        # 类原始路径
        prim_path = hou.StringParmTemplate("shader_baseprimpath", "Class Prim Path", 1,
                                           default_value=(["/__class_mtl__/`$OS`"]))
        folder.addParmTemplate(prim_path)

        # 分隔符
        folder.addParmTemplate(hou.SeparatorParmTemplate("separator1"))

        # 标签菜单掩码
        tab_mask = hou.StringParmTemplate("tabmenumask", "Tab Menu Mask", 1,
                                          default_value=([
                                              "MaterialX parameter constant collect null genericshader subnet subnetconnector suboutput subinput"]))
        folder.addParmTemplate(tab_mask)

        # 渲染上下文名称
        context_name = hou.StringParmTemplate("shader_rendercontextname", "Render Context Name", 1,
                                              default_value=(["mtlx"]))
        folder.addParmTemplate(context_name)

        # 强制转换子节点
        force_children = hou.ToggleParmTemplate("shader_forcechildren", "Force Translation of Children", True)
        folder.addParmTemplate(force_children)

        # 添加到参数组
        parm_template_group.append(folder)

        # 应用参数模板组
        subnet.setParmTemplateGroup(parm_template_group)

        return subnet

    def _set_base_parameters(self, std_surface):
        """Set base parameters from Arnold material"""
        attributes = self.material_data.get("attributes", {})

        # 设置浮点参数
        float_params = ["specular", "specularRoughness", "metalness",
                        "transmission", "subsurface", "sheen", "coat"]

        for param in float_params:
            if param in attributes:
                value = attributes[param]
                if std_surface.parm(param):
                    std_surface.parm(param).set(value)

        # 设置颜色参数
        for arnold_param, mtlx_param in self.ARNOLD_TO_MTLX_MAPPING.items():
            if arnold_param in attributes:
                color_value = attributes[arnold_param]
                if isinstance(color_value, list) and len(color_value) == 3:
                    # 设置RGB分量
                    if std_surface.parm(f"{mtlx_param}r"):
                        std_surface.parm(f"{mtlx_param}r").set(color_value[0])
                    if std_surface.parm(f"{mtlx_param}g"):
                        std_surface.parm(f"{mtlx_param}g").set(color_value[1])
                    if std_surface.parm(f"{mtlx_param}b"):
                        std_surface.parm(f"{mtlx_param}b").set(color_value[2])
                else:
                    # 单值参数
                    if std_surface.parm(mtlx_param):
                        std_surface.parm(mtlx_param).set(color_value)

    def _process_connections(self, material_lib):
        """Process all connections defined in the JSON"""
        connections = self.material_data.get("connections", {})

        for target_param, connection_list in connections.items():
            for connection in connection_list:
                source_node_name = connection.get("node")
                source_attr = connection.get("source_attribute")
                target_attr = connection.get("target_attribute", target_param)

                # 确保源节点存在
                if source_node_name not in self.json_data:
                    continue

                # 创建源节点（如果尚未创建）
                if source_node_name not in self.created_nodes:
                    self._create_node(source_node_name, material_lib)

                # 连接节点
                if (source_node_name in self.created_nodes and
                        self.material_name in self.created_nodes):
                    source_node = self.created_nodes[source_node_name]
                    target_node = self.created_nodes[self.material_name]

                    # 获取目标参数的输入索引
                    input_index = self._get_input_index(target_node, target_attr)

                    if input_index is not None:
                        target_node.setInput(input_index, source_node)

    def _create_node(self, node_name, material_lib):
        """Create a node based on its type in JSON"""
        if node_name not in self.json_data:
            return

        node_data = self.json_data[node_name]
        node_type = node_data.get("type", "")

        # 获取MaterialX等效节点类型
        arnold_node_type = node_type.split(":")[0]
        mtlx_node_type = self.ARNOLD_NODE_MAPPING.get(arnold_node_type, "")
        if not mtlx_node_type:
            return

        # 获取父节点（材质子网）
        parent_node = material_lib.node(self.material_name)
        if not parent_node:
            raise RuntimeError(f"Parent material subnet not found: {self.material_name}")

        # 创建节点
        node = parent_node.createNode(mtlx_node_type, node_name)
        self.created_nodes[node_name] = node

        # 设置节点参数
        self._set_node_parameters(node, node_data)

        # 处理此节点的连接
        connections = node_data.get("connections", {})
        for target_param, connection_list in connections.items():
            for connection in connection_list:
                source_node_name = connection.get("node")
                source_attr = connection.get("source_attribute")
                target_attr = connection.get("target_attribute", target_param)

                # 确保源节点存在
                if source_node_name not in self.json_data:
                    continue

                # 创建源节点（如果尚未创建）
                if source_node_name not in self.created_nodes:
                    self._create_node(source_node_name, material_lib)

                # 连接节点
                if source_node_name in self.created_nodes:
                    source_node = self.created_nodes[source_node_name]

                    # 获取目标参数的输入索引
                    input_index = self._get_input_index(node, target_attr)

                    if input_index is not None:
                        node.setInput(input_index, source_node)

        return node

    def _set_node_parameters(self, node, node_data):
        """Set parameters for a node based on JSON data"""
        attributes = node_data.get("attributes", {})

        # 图像节点的特殊处理
        if node.type().name() == "mtlximage":
            if "filename" in attributes:
                file_path = attributes["filename"]
                node.parm("file").set(file_path)

                # 根据参数类型设置颜色空间
                if "color" in node_data.get("type", "").lower():
                    node.parm("filecolorspace").set("srgb_tx")
                else:
                    node.parm("filecolorspace").set("raw")

        # 设置其他参数
        for param, value in attributes.items():
            if node.parm(param) is not None:
                # 处理颜色参数
                if isinstance(value, list) and len(value) == 3:
                    if node.parm(f"{param}r") is not None:
                        node.parm(f"{param}r").set(value[0])
                    if node.parm(f"{param}g") is not None:
                        node.parm(f"{param}g").set(value[1])
                    if node.parm(f"{param}b") is not None:
                        node.parm(f"{param}b").set(value[2])
                else:
                    node.parm(param).set(value)

    def _get_input_index(self, node, parameter_name):
        """Get input index for a parameter by name"""
        # 获取所有输入
        inputs = node.inputs()

        # 尝试直接匹配
        for i, input in enumerate(inputs):
            if input.name() == parameter_name:
                return i

        # 尝试映射名称
        mtlx_param = self.ARNOLD_TO_MTLX_MAPPING.get(parameter_name, "")
        if mtlx_param:
            for i, input in enumerate(inputs):
                if input.name() == mtlx_param:
                    return i

        return None

    def _create_output_nodes(self, subnet, std_surface):
        """Create output nodes for the material"""
        # 创建表面输出
        surface_out = subnet.createNode("subnetconnector", "surface_output")
        surface_out.parm("connectorkind").set("output")
        surface_out.parm('parmname').set("surface")
        surface_out.parm('parmlabel').set("Surface")
        surface_out.parm('parmtype').set("surface")
        surface_out.setInput(0, std_surface)
        surface_out.setColor(hou.Color(0.89, 0.69, 0.6))

        # 如果存在置换则创建置换输出
        if std_surface.parm("disp") and std_surface.parm("disp").eval() > 0:
            disp_out = subnet.createNode("subnetconnector", "displacement_output")
            disp_out.parm("connectorkind").set("output")
            disp_out.parm('parmname').set("displacement")
            disp_out.parm('parmlabel').set("Displacement")
            disp_out.parm('parmtype').set("displacement")
            disp_out.setColor(hou.Color(0.6, 0.69, 0.89))
            # 连接置换节点
            if std_surface.parm("disp"):
                disp_out.setInput(0, std_surface, 0)


# 在Houdini中运行工具
def show_arnold_to_mtlx_tool():
    # 关闭现有窗口
    # for win in QtWidgets.QApplication.topLevelWindows():
    # if win.windowTitle() == "Arnold to MaterialX Converter":
    # win.close()

    # 创建新窗口
    window = JsonToMtlx()
    window.show()
    return window


# 启动工具
show_arnold_to_mtlx_tool()