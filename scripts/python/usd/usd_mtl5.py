# coding: utf-8
from PySide2 import QtWidgets, QtCore, QtGui
from shiboken2 import wrapInstance
import maya.OpenMaya as OM
import maya.cmds as cmds
import re
import os
from maya.app.general.mayaMixin import MayaQWidgetBaseMixin
from pxr import Usd, UsdGeom, Gf, Sdf, Vt, UsdShade


class UsdMtlExport:
    def export_arnold_material_to_usd(self, file_path, selected_objects=None):
        """导出 Arnold 材质到 USD（带MaterialX nodeGraph封装）"""
        if not selected_objects:
            selected_objects = cmds.ls(selection=True, long=True)
        if not selected_objects:
            cmds.warning("未选中任何对象！")
            return False

        # 创建USD舞台
        stage = Usd.Stage.CreateNew(file_path)
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)

        # 设置根Prim
        root_prim = stage.OverridePrim("/Root")
        stage.SetDefaultPrim(root_prim)

        # 创建MaterialX层级结构
        mtlx_root = stage.DefinePrim("/Root/MaterialX", "Scope")
        stage.DefinePrim("/Root/MaterialX/Materials", "Scope")  # 最终材质
        stage.DefinePrim("/Root/MaterialX/NodeGraphs", "Scope")  # 材质网络

        # 材质字典（避免重复创建）
        material_dict = {}

        # 导出选中的每个根节点及其子层级
        for root in selected_objects:
            self.export_node(stage, root, '/Root', material_dict)

        # 保存文件
        stage.GetRootLayer().Save()
        cmds.inViewMessage(
            message=f"Successfully exported to: {file_path}",
            position="botRight",
            fade=True,
            fadeStayTime=2000
        )
        return True

    def export_node(self, stage, maya_node_path, usd_parent_path, material_dict):
        """递归导出节点层级"""
        node_name = maya_node_path.split('|')[-1].replace(':', '_')
        usd_path = f"{usd_parent_path}/{node_name}"

        node_type = cmds.nodeType(maya_node_path)

        if node_type == 'transform':
            xform_prim = stage.OverridePrim(usd_path)
        elif node_type == "mesh":
            mesh_prim = stage.OverridePrim(usd_path)
            self.bind_materials(maya_node_path, stage, mesh_prim, material_dict)

        # 递归处理子节点
        children = cmds.listRelatives(maya_node_path, children=True, fullPath=True) or []
        for child in children:
            self.export_node(stage, child, usd_path, material_dict)

    def bind_materials(self, maya_mesh_path, stage, usd_prim, material_dict):
        """绑定材质到Prim（使用MaterialX结构）"""
        shading_groups = cmds.listConnections(maya_mesh_path, type="shadingEngine") or []
        if not shading_groups:
            return

        for sg in shading_groups:
            materials = cmds.listConnections(sg + ".surfaceShader") or []
            if not materials:
                continue

            material = materials[0]
            material_name = material.replace(':', '_')
            material_path = f"/Root/MaterialX/Materials/{material_name}"

            if material_name not in material_dict:
                self.export_mx_standard_surface(stage, material_path, material)
                material_dict[material_name] = material_path

            # 绑定最终材质（不是nodeGraph）
            binding_api = UsdShade.MaterialBindingAPI(usd_prim)
            material_prim = stage.GetPrimAtPath(material_path)
            binding_api.Bind(UsdShade.Material(material_prim))

    def export_mx_standard_surface(self, stage, usd_material_path, maya_material):
        """新版：将材质网络封装在nodeGraph中"""
        material_name = usd_material_path.split("/")[-1]
        mtlx_path = "/Root/MaterialX"
        nodegraph_path = f"{mtlx_path}/NodeGraphs/{material_name}_NG"
        shader_path = f"{nodegraph_path}/Shader"

        # 创建NodeGraph容器
        nodegraph_prim = stage.DefinePrim(nodegraph_path, "NodeGraph")

        # 在NodeGraph内创建标准表面着色器
        shader = UsdShade.Shader.Define(stage, shader_path)
        shader.CreateIdAttr("ND_standard_surface_surfaceshader")

        # Arnold属性映射表
        attribute_map = {
            "base": "base",
            "baseColor": "base_color",
            "diffuseRoughness": "diffuse_roughness",
            # ...其他属性映射...
        }

        for maya_attr, arnold_attr in attribute_map.items():
            if not cmds.attributeQuery(maya_attr, node=maya_material, exists=True):
                continue

            is_color = maya_attr.endswith("Color") or maya_attr in ['baseColor', 'emissionColor']
            connected_nodes = cmds.listConnections(
                f"{maya_material}.{maya_attr}",
                source=True,
                destination=False,
                plugs=True
            ) or []

            if connected_nodes:
                source_node = connected_nodes[0].split('.')[0]
                node_type = cmds.nodeType(source_node)

                if node_type in ["file", "aiImage"]:
                    self.export_arnold_texture(
                        stage, source_node, shader, arnold_attr, nodegraph_path)
                elif node_type == 'aiColorCorrect':
                    texture_node = self.get_connected_texture(source_node, 'input')
                    if texture_node:
                        self.export_color_correct_network(
                            stage, texture_node, source_node,
                            shader, arnold_attr, nodegraph_path, is_color)
            else:
                value = cmds.getAttr(f"{maya_material}.{maya_attr}")
                if isinstance(value, (list, tuple)) and len(value[0]) >= 3 and is_color:
                    shader.CreateInput(arnold_attr, Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*value[:3]))
                else:
                    scalar_value = self.get_scalar_value(value)
                    shader.CreateInput(arnold_attr, Sdf.ValueTypeNames.Float).Set(scalar_value)

        # 特殊处理法线贴图
        self.export_arnold_normal_map(stage, maya_material, shader, nodegraph_path)

        # 创建最终材质并连接nodeGraph
        material_prim = stage.DefinePrim(usd_material_path, "Material")
        usd_material = UsdShade.Material(material_prim)

        # nodeGraph输出接口
        ng_output = UsdShade.Output(nodegraph_prim, "out")
        ng_output.ConnectToSource(shader.ConnectableAPI(), "surface")

        # 材质连接到nodeGraph
        usd_material.CreateSurfaceOutput().ConnectToSource(ng_output)

    def export_color_correct_network(self, stage, texture_node, color_correct_node,
                                     usd_shader, arnold_attr, parent_path, is_color):
        """在nodeGraph内导出颜色校正网络"""
        texture_name = f"{arnold_attr}.texture"
        texture_shader = UsdShade.Shader.Define(stage, f"{parent_path}/{texture_name}")
        texture_shader.CreateIdAttr("ND_image_color3")

        texture_path = self.get_texture_path(texture_node)
        if texture_path:
            texture_shader.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(texture_path)

        # 颜色校正节点
        cc_name = f"{arnold_attr}.color_correct"
        cc_shader = UsdShade.Shader.Define(stage, f"{parent_path}/{cc_name}")
        cc_shader.CreateIdAttr("ND_colorcorrect_color3")

        # 映射属性...
        cc_attrs = {
            "gamma": "gamma",
            "saturation": "saturation",
            # ...其他属性...
        }
        for maya_attr, usd_attr in cc_attrs.items():
            value = cmds.getAttr(f"{color_correct_node}.{maya_attr}")
            if isinstance(value, (list, tuple)) and len(value) >= 3:
                cc_shader.CreateInput(usd_attr, Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*value[:3]))
            else:
                cc_shader.CreateInput(usd_attr, Sdf.ValueTypeNames.Float).Set(self.get_scalar_value(value))

        # 连接节点
        texture_shader.CreateOutput("out", Sdf.ValueTypeNames.Color3f)
        cc_shader.CreateInput("in", Sdf.ValueTypeNames.Color3f).ConnectToSource(
            texture_shader.ConnectableAPI(), "out"
        )

        # 连接到主着色器
        output_type = Sdf.ValueTypeNames.Color3f if is_color else Sdf.ValueTypeNames.Float
        cc_shader.CreateOutput("out", output_type)
        usd_shader.CreateInput(arnold_attr, output_type).ConnectToSource(
            cc_shader.ConnectableAPI(), "out"
        )

    def export_arnold_normal_map(self, stage, maya_material, usd_shader, parent_path):
        """在nodeGraph内处理法线贴图"""
        normal_nodes = cmds.listConnections(
            f"{maya_material}.normalCamera",
            source=True,
            destination=False,
            type='bump2d'
        ) or []

        for node in normal_nodes:
            if cmds.nodeType(node) == 'aiNormalMap':
                texture_node = self.get_connected_texture(node, 'input')
                strength = cmds.getAttr(f"{node}.strength")
            else:  # bump2d
                texture_node = self.get_connected_texture(node, 'bumpValue')
                strength = cmds.getAttr(f"{node}.bumpDepth")

            if not texture_node:
                continue

            texture_path = self.get_texture_path(texture_node)
            if not texture_path:
                continue

            # 纹理节点
            tex_shader = UsdShade.Shader.Define(stage, f"{parent_path}/normal_texture")
            tex_shader.CreateIdAttr("ND_image_color3")
            tex_shader.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(texture_path)
            tex_shader.CreateOutput("out", Sdf.ValueTypeNames.Color3f)

            # 法线节点
            normal_shader = UsdShade.Shader.Define(stage, f"{parent_path}/normal_map")
            normal_shader.CreateIdAttr("ND_normalmap")
            normal_shader.CreateInput("strength", Sdf.ValueTypeNames.Float).Set(strength)
            normal_shader.CreateInput("in", Sdf.ValueTypeNames.Color3f).ConnectToSource(
                tex_shader.ConnectableAPI(), "out"
            )

            # 连接到主着色器
            usd_shader.CreateInput("normal", Sdf.ValueTypeNames.Vector3f).ConnectToSource(
                normal_shader.ConnectableAPI(), "out"
            )

    def get_texture_path(self, texture_node):
        """获取纹理路径并处理UDIM"""
        if cmds.nodeType(texture_node) == "file":
            path = cmds.getAttr(f"{texture_node}.fileTextureName")
        elif cmds.nodeType(texture_node) == "aiImage":
            path = cmds.getAttr(f"{texture_node}.filename")
        else:
            return ""

        if "<UDIM>" not in path and re.search(r'\d{4}', path):
            dirname, filename = os.path.split(path)
            new_filename = re.sub(r'\d{4}', '<UDIM>', filename)
            return os.path.join(dirname, new_filename)
        return path

    def get_connected_texture(self, node, attribute):
        """获取连接的纹理节点"""
        connections = cmds.listConnections(
            f"{node}.{attribute}",
            source=True,
            destination=False,
            type=["file", "aiImage"]
        ) or []
        return connections[0] if connections else None

    def get_scalar_value(self, value):
        """提取标量值"""
        while isinstance(value, (list, tuple)):
            value = value[0] if len(value) > 0 else 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0