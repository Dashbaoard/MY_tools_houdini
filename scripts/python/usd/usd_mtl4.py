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
        """导出 Arnold 材质到 USD"""
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

        # 创建材质根目录（Scope类型）
        materials_root = stage.DefinePrim("/Root/Materials", "Scope")

        # 材质字典（避免重复创建）
        material_dict = {}

        # 导出选中的每个根节点及其子层级
        for root in selected_objects:
            self.export_node(stage, root, '/Root', material_dict)

        # 保存文件
        stage.GetRootLayer().Save()
        cmds.inViewMessage(message=f"Successfully exported to: {file_path}",
                           position="botRight", fade=True, fadeStayTime=2000)
        return True

    def export_node(self, stage, maya_node_path, usd_parent_path, material_dict):
        """递归导出节点层级"""
        # 生成合法的USD路径名称
        node_name = maya_node_path.split('|')[-1].replace(':', '_')
        usd_path = f"{usd_parent_path}/{node_name}"

        node_type = cmds.nodeType(maya_node_path)

        if node_type == 'transform':
            xform_prim = stage.OverridePrim(usd_path)

        # 如果是mesh节点，处理材质绑定
        elif node_type == "mesh":
            mesh_prim = stage.OverridePrim(usd_parent_path)
            self.bind_materials(maya_node_path, stage, mesh_prim, material_dict)

        # 递归处理子节点
        children = cmds.listRelatives(maya_node_path, children=True, fullPath=True) or []
        for child in children:
            self.export_node(stage, child, usd_path, material_dict)

    def bind_materials(self, maya_mesh_path, stage, usd_prim, material_dict):
        """绑定材质到Prim"""
        shading_groups = cmds.listConnections(maya_mesh_path, type="shadingEngine") or []
        if not shading_groups:
            return

        for sg in shading_groups:
            materials = cmds.listConnections(sg + ".surfaceShader") or []
            if not materials:
                continue

            material = materials[0]
            material_name = material.replace(':', '_')
            material_path = f"/Root/Materials/{material_name}"

            # 创建材质（如果尚未存在）
            if material_name not in material_dict:
                self.export_mx_standard_surface(stage, material_path, material)
                material_dict[material_name] = material_path

            # 绑定材质
            binding_api = UsdShade.MaterialBindingAPI(usd_prim)
            material_prim = stage.GetPrimAtPath(material_dict[material_name])
            binding_api.Bind(UsdShade.Material(material_prim))

    def export_mx_standard_surface(self, stage, usd_material_path, maya_material):
        """导出为 arnold:standard_surface 材质"""
        usd_material = UsdShade.Material.Define(stage, usd_material_path)
        shader = UsdShade.Shader.Define(stage, f"{usd_material_path}/Shader")
        shader.CreateIdAttr("ND_standard_surface_surfaceshader")

        # Arnold属性映射表
        attribute_map = {
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

        for maya_attr, arnold_attr in attribute_map.items():
            if not cmds.attributeQuery(maya_attr, node=maya_material, exists=True):
                continue

            # 检查是否是颜色属性
            is_color = maya_attr.endswith("Color") or maya_attr in ['baseColor', 'emissionColor']

            # 处理连接
            connected_nodes = cmds.listConnections(
                f"{maya_material}.{maya_attr}",
                source=True,
                destination=False,
                plugs=True
            ) or []

            if connected_nodes:
                # 获取直接连接的节点
                source_node = connected_nodes[0].split('.')[0]
                node_type = cmds.nodeType(source_node)

                if node_type in ["file", "aiImage"]:
                    self.export_arnold_texture(stage, source_node, shader, arnold_attr, usd_material_path)
                elif node_type == 'aiColorCorrect':
                    texture_node = self.get_connected_texture(source_node, 'input')
                    if not texture_node:
                        texture_node = self.get_connected_texture(source_node, 'input.inputR')
                    if texture_node:
                        self.export_color_correct_network(stage, texture_node, source_node,
                                                          shader, arnold_attr, usd_material_path, is_color)
            else:
                # 处理普通属性值
                value = cmds.getAttr(f"{maya_material}.{maya_attr}")
                if isinstance(value, (list, tuple)) and len(value[0]) >= 3 and is_color:
                    shader.CreateInput(arnold_attr, Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*value[:3]))
                else:
                    scalar_value = self.get_scalar_value(value)
                    shader.CreateInput(arnold_attr, Sdf.ValueTypeNames.Float).Set(scalar_value)

        # 特殊处理法线贴图
        self.export_arnold_normal_map(stage, maya_material, shader, usd_material_path)

        usd_material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")

    def export_color_correct_network(self, stage, texture_node, color_correct_node,
                                     usd_shader, arnold_attr, material_path, is_color):
        """导出包含颜色校正节点的网络"""
        # 1. 导出纹理
        texture_name = f"{arnold_attr}.texture"
        texture_shader = UsdShade.Shader.Define(stage, f"{material_path}/{texture_name}")
        texture_shader.CreateIdAttr("ND_image_color3")

        texture_path = ""
        if cmds.nodeType(texture_node) == "file":
            texture_path = cmds.getAttr(f"{texture_node}.fileTextureName")
            if "<UDIM>" in texture_path:
                pass
            else:
                dirname, filename = os.path.split(texture_path)
                new_filename = re.sub(r'1\d{3}', '<UDIM>', filename)
                texture_path = os.path.join(dirname, new_filename)

        elif cmds.nodeType(texture_node) == 'aiImage':
            texture_path = cmds.getAttr(f"{texture_node}.filename")

        if texture_path:
            texture_shader.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(texture_path)

        # 2. 导出颜色校正
        color_correct_name = f"{arnold_attr}.color_correct"
        color_correct_shader = UsdShade.Shader.Define(stage, f"{material_path}/{color_correct_name}")
        color_correct_shader.CreateIdAttr("ND_colorcorrect_color3")

        # 映射属性
        color_correct_attrs = {
            "input": "input",
            "gamma": "gamma",
            "saturation": "saturation",
            "contrast": "contrast",
            "contrastPivot": "contrast_pivot",
            "exposure": "exposure",
            "multiply": "multiply"
        }

        for maya_attr, usd_attr in color_correct_attrs.items():
            value = cmds.getAttr(f"{color_correct_node}.{maya_attr}")
            if isinstance(value, (list, tuple)) and len(value) >= 3:
                color_correct_shader.CreateInput(usd_attr, Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*value[:3]))
            else:
                scalar_value = self.get_scalar_value(value)
                color_correct_shader.CreateInput(usd_attr, Sdf.ValueTypeNames.Float).Set(scalar_value)

        # 3. 连接节点
        texture_shader.CreateOutput("out", Sdf.ValueTypeNames.Color3f)
        color_correct_shader.CreateInput("in", Sdf.ValueTypeNames.Color3f).ConnectToSource(
            texture_shader.ConnectableAPI(), "out"
        )

        # 4. 连接到材质
        if is_color:
            color_correct_shader.CreateOutput("out", Sdf.ValueTypeNames.Color3f)
            usd_shader.CreateInput(arnold_attr, Sdf.ValueTypeNames.Color3f).ConnectToSource(
                color_correct_shader.ConnectableAPI(), "out"
            )
        else:
            color_correct_shader.CreateOutput("out", Sdf.ValueTypeNames.Float)
            usd_shader.CreateInput(arnold_attr, Sdf.ValueTypeNames.Float).ConnectToSource(
                color_correct_shader.ConnectableAPI(), "out"
            )



    def export_arnold_normal_map(self, stage, maya_material, usd_shader, material_path):
        """处理 Arnold 法线贴图"""
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

            texture_path = ""
            if cmds.nodeType(texture_node) == "file":
                texture_path = cmds.getAttr(f"{texture_node}.fileTextureName")
                if "<UDIM>" in texture_path:
                    pass
                else:
                    dirname, filename = os.path.split(texture_path)
                    new_filename = re.sub(r'1\d{3}', '<UDIM>', filename)
                    texture_path = os.path.join(dirname, new_filename)

            elif cmds.nodeType(texture_node) == 'aiImage':
                texture_path = cmds.getAttr(f"{texture_node}.filename")

            if not texture_path:
                continue

            # 1.创建 Arnold:image节点
            tex_shader = UsdShade.Shader.Define(stage, f"{material_path}/normal_texture")
            tex_shader.CreateIdAttr("ND_image_color3")
            tex_shader.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(texture_path)
            tex_shader.CreateOutput("out", Sdf.ValueTypeNames.Color3f)

            # 2.创建 Arnold:normal_map节点
            normal_shader = UsdShade.Shader.Define(stage, f"{material_path}/normal_map")
            normal_shader.CreateIdAttr("ND_normalmap")
            normal_shader.CreateInput("strength", Sdf.ValueTypeNames.Float).Set(strength)
            normal_shader.CreateInput("in", Sdf.ValueTypeNames.Color3f).ConnectToSource(
                tex_shader.ConnectableAPI(), "out"
            )

            # 3.连接到对应的 normal属性
            usd_shader.CreateInput("normal", Sdf.ValueTypeNames.Vector3f).ConnectToSource(
                normal_shader.ConnectableAPI(), "out"
            )

    def get_connected_texture(self, node, attribute):
        """获取连接的纹理节点"""
        #for attr in attributes:
        connections = cmds.listConnections(
            f"{node}.{attribute}",
            source=True,
            destination=False,
            type="file"
        ) or []
        return connections[0] if connections else None

    def export_arnold_texture(self, stage, maya_texture_node, usd_shader, arnold_attr, material_path):
        """导出纹理节点"""
        texture_name = f"{arnold_attr}.texture"
        texture_shader = UsdShade.Shader.Define(stage, f"{material_path}/{texture_name}")
        texture_shader.CreateIdAttr("ND_image_color3")

        texture_path = ""
        if cmds.nodeType(maya_texture_node) == "file":
            texture_path = cmds.getAttr(f"{maya_texture_node}.fileTextureName")
            if "<UDIM>" in texture_path:
                pass
            else:
                dirname, filename = os.path.split(texture_path)
                new_filename = re.sub(r'1\d{3}', '<UDIM>', filename)
                texture_path = os.path.join(dirname, new_filename)

        elif cmds.nodeType(maya_texture_node) == "aiImage":
            texture_path = cmds.getAttr(f"{maya_texture_node}.filename")

        if texture_path:
            texture_shader.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(texture_path)

        # 连接到材质
        is_color = arnold_attr.endswith("_color") or arnold_attr == "base_color"
        if is_color:
            texture_shader.CreateOutput("out", Sdf.ValueTypeNames.Color3f)
            usd_shader.CreateInput(arnold_attr, Sdf.ValueTypeNames.Color3f).ConnectToSource(
                texture_shader.ConnectableAPI(), "out"
            )
        else:
            texture_shader.CreateOutput("out", Sdf.ValueTypeNames.Float)
            usd_shader.CreateInput(arnold_attr, Sdf.ValueTypeNames.Float).ConnectToSource(
                texture_shader.ConnectableAPI(), "out"
            )
    def get_scalar_value(self, value):
        """递归提取标量值"""
        while isinstance(value, (list, tuple)):
            if len(value) == 0:
                return 0.0
            value = value[0]
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0