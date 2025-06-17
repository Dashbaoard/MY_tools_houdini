# _*_ coding: utf-8 _*_
# .@FileName:usd_mtl3
# .@Date....:2025-06-09 : 22 : 27
# .@Aurhor..:冥羽
# .@Contact.:1942598111@qq.com
'''
launch:
        import usd_mtl3 as Qs_FileName
        reload(FileName)
        FileName.main()
'''
import maya.cmds as cmds
from pxr import Usd, UsdShade, UsdGeom, Sdf, Gf, Kind


def export_arnold_material_to_usd(file_path, selected_objects=None):
    """导出 Arnold 材质到 USD (使用 arnold:standard_surface)"""
    if not selected_objects:
        selected_objects = cmds.ls(selection=True, long=True, dag=True, type=["mesh", "transform"])
    if not selected_objects:
        cmds.warning("未选中任何对象！")
        return False

    stage = Usd.Stage.CreateNew(file_path)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)

    root_prim = stage.DefinePrim("/Root")
    stage.SetDefaultPrim(root_prim)
    Usd.ModelAPI(root_prim).SetKind(Kind.Tokens.component)

    materials_scope = stage.DefinePrim("/Root/Materials", "Scope")
    geometry_scope = stage.DefinePrim("/Root/Geometry", "Scope")

    material_bindings = {}
    for obj in selected_objects:
        if cmds.nodeType(obj) == "transform":
            meshes = cmds.listRelatives(obj, allDescendents=True, type="mesh", fullPath=True) or []
            for mesh in meshes:
                process_mesh(mesh, stage, geometry_scope, materials_scope, material_bindings)
        elif cmds.nodeType(obj) == "mesh":
            process_mesh(obj, stage, geometry_scope, materials_scope, material_bindings)

    stage.GetRootLayer().Save()
    print(f"USD 文件已保存: {file_path}")
    return True


def process_mesh(maya_mesh_path, stage, geometry_scope, materials_scope, material_bindings):
    mesh_name = maya_mesh_path.split("|")[-1].replace(":", "_")
    usd_mesh_path = f"{geometry_scope.GetPath()}/{mesh_name}"
    usd_mesh = UsdGeom.Mesh.Define(stage, usd_mesh_path)

    shading_groups = cmds.listConnections(maya_mesh_path, type="shadingEngine") or []
    for sg in shading_groups:
        material = get_arnold_material(sg)
        if not material:
            continue

        material_name = material.replace(":", "_")
        material_path = f"{materials_scope.GetPath()}/{material_name}"
        if material_name not in material_bindings:
            export_arnold_standard_surface(stage, material_path, material)
            material_bindings[material_name] = material_path

        binding_api = UsdShade.MaterialBindingAPI(usd_mesh)
        binding_api.Bind(UsdShade.Material(stage.GetPrimAtPath(material_bindings[material_name])))


def export_arnold_standard_surface(stage, usd_material_path, maya_material):
    """导出为 arnold:standard_surface 材质"""
    usd_material = UsdShade.Material.Define(stage, usd_material_path)
    shader = UsdShade.Shader.Define(stage, f"{usd_material_path}/Shader")
    shader.CreateIdAttr("ND_standard_surface_surfaceshader")

    attribute_map = {
        "baseColor": "base_color",
        "base": "base",
        "baseWeight": "base",
        "diffuseRoughness": "diffuse_roughness",
        "specularColor": "specular_color",
        "specularRoughness": "specular_roughness",
        "specularIOR": "specular_IOR",
        "specularAnisotropy": "specular_anisotropy",
        "metalness": "metalness",
        "emissionColor": "emission_color",
        "emissionWeight": "emission",
        "opacity": "opacity",
    }

    for maya_attr, arnold_attr in attribute_map.items():
        if not cmds.attributeQuery(maya_attr, node=maya_material, exists=True):
            continue

        # 检查是否是颜色属性
        is_color = maya_attr.endswith("Color") or maya_attr in ["baseColor", "emissionColor"]

        # 处理连接
        connected_nodes = cmds.listConnections(
            f"{maya_material}.{maya_attr}",
            source=True,
            destination=False,
            plugs=True
        ) or []

        if connected_nodes:
            # 获取直接连接的节点
            source_node = connected_nodes[0].split(".")[0]
            node_type = cmds.nodeType(source_node)

            if node_type in ["file", "aiImage"]:
                export_arnold_texture(stage, source_node, shader, arnold_attr, usd_material_path)
            elif node_type == "aiColorCorrect":
                # 获取纹理输入
                texture_node = get_connected_texture(source_node, "input")
                if texture_node:
                    export_color_correct_network(
                        stage,
                        texture_node,
                        source_node,
                        shader,
                        arnold_attr,
                        usd_material_path,
                        is_color
                    )
        else:
            # 处理普通属性值
            value = cmds.getAttr(f"{maya_material}.{maya_attr}")
            if isinstance(value, (list, tuple)) and len(value) >= 3 and is_color:
                shader.CreateInput(arnold_attr, Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*value[:3]))
            else:
                scalar_value = get_scalar_value(value)
                shader.CreateInput(arnold_attr, Sdf.ValueTypeNames.Float).Set(scalar_value)

    # 特殊处理法线贴图
    export_arnold_normal_map(stage, maya_material, shader, usd_material_path)

    usd_material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")


def export_color_correct_network(
        stage,
        texture_node,
        color_correct_node,
        usd_shader,
        arnold_attr,
        material_path,
        is_color
):
    """导出包含颜色校正节点的网络"""
    # 1. 导出纹理
    texture_name = f"{arnold_attr}_texture"
    texture_shader = UsdShade.Shader.Define(stage, f"{material_path}/{texture_name}")
    texture_shader.CreateIdAttr("arnold:image")

    texture_path = ""
    if cmds.nodeType(texture_node) == "file":
        texture_path = cmds.getAttr(f"{texture_node}.fileTextureName")
    elif cmds.nodeType(texture_node) == "aiImage":
        texture_path = cmds.getAttr(f"{texture_node}.filename")

    if texture_path:
        texture_shader.CreateInput("filename", Sdf.ValueTypeNames.Asset).Set(texture_path)

    # 2. 导出颜色校正
    color_correct_name = f"{arnold_attr}_color_correct"
    color_correct_shader = UsdShade.Shader.Define(stage, f"{material_path}/{color_correct_name}")
    color_correct_shader.CreateIdAttr("arnold:color_correct")

    # 映射属性
    color_correct_attrs = {
        "exposure": "exposure",
        "gamma": "gamma",
        "contrast": "contrast",
        "hueShift": "hue_shift",
        "saturation": "saturation",
        "gain": "gain",
        "offset": "offset",
        "mask": "mask"
    }

    for maya_attr, usd_attr in color_correct_attrs.items():
        if cmds.attributeQuery(maya_attr, node=color_correct_node, exists=True):
            value = cmds.getAttr(f"{color_correct_node}.{maya_attr}")
            if isinstance(value, (list, tuple)):
                value = value[0]
            color_correct_shader.CreateInput(usd_attr, Sdf.ValueTypeNames.Float).Set(float(value))

    # 3. 连接节点
    texture_shader.CreateOutput("out", Sdf.ValueTypeNames.Color3f)
    color_correct_shader.CreateInput("input", Sdf.ValueTypeNames.Color3f).ConnectToSource(
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


def export_arnold_texture(stage, maya_texture_node, usd_shader, arnold_attr, material_path):
    """导出纹理节点"""
    texture_name = f"{arnold_attr}_texture"
    texture_shader = UsdShade.Shader.Define(stage, f"{material_path}/{texture_name}")
    texture_shader.CreateIdAttr("arnold:image")

    texture_path = ""
    if cmds.nodeType(maya_texture_node) == "file":
        texture_path = cmds.getAttr(f"{maya_texture_node}.fileTextureName")
    elif cmds.nodeType(maya_texture_node) == "aiImage":
        texture_path = cmds.getAttr(f"{maya_texture_node}.filename")

    if texture_path:
        texture_shader.CreateInput("filename", Sdf.ValueTypeNames.Asset).Set(texture_path)

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


def export_arnold_normal_map(stage, maya_material, usd_shader, material_path):
    """处理 Arnold 法线贴图"""
    normal_nodes = cmds.listConnections(
        f"{maya_material}.normalCamera",
        source=True,
        destination=False,
        type="bump2d"
    ) or []

    for node in normal_nodes:
        if cmds.nodeType(node) == "aiNormalMap":
            texture_node = get_connected_texture(node, "input")
            strength = cmds.getAttr(f"{node}.strength")
        else:  # bump2d
            texture_node = get_connected_texture(node, "bumpValue")
            strength = cmds.getAttr(f"{node}.bumpDepth")

        if not texture_node:
            continue

        texture_path = ""
        if cmds.nodeType(texture_node) == "file":
            texture_path = cmds.getAttr(f"{texture_node}.fileTextureName")
        elif cmds.nodeType(texture_node) == "aiImage":
            texture_path = cmds.getAttr(f"{texture_node}.filename")

        if not texture_path:
            continue

        # 1. 创建 arnold:image 节点
        tex_shader = UsdShade.Shader.Define(stage, f"{material_path}/normal_texture")
        tex_shader.CreateIdAttr("arnold:image")
        tex_shader.CreateInput("filename", Sdf.ValueTypeNames.Asset).Set(texture_path)
        tex_shader.CreateOutput("out", Sdf.ValueTypeNames.Color3f)

        # 2. 创建 arnold:normal_map 节点
        normal_shader = UsdShade.Shader.Define(stage, f"{material_path}/normal_map")
        normal_shader.CreateIdAttr("arnold:normal_map")
        normal_shader.CreateInput("strength", Sdf.ValueTypeNames.Float).Set(strength)
        normal_shader.CreateInput("input", Sdf.ValueTypeNames.Color3f).ConnectToSource(
            tex_shader.ConnectableAPI(), "out"
        )

        # 3. 连接到材质的 normal 属性
        usd_shader.CreateInput("normal", Sdf.ValueTypeNames.Vector3f).ConnectToSource(
            normal_shader.ConnectableAPI(), "out"
        )


# 辅助函数
def get_arnold_material(shading_group):
    materials = cmds.listConnections(
        f"{shading_group}.surfaceShader",
        type="aiStandardSurface"
    ) or []
    return materials[0] if materials else None


def get_connected_texture(node, attribute):
    connections = cmds.listConnections(
        f"{node}.{attribute}",
        source=True,
        destination=False,
        type="file"
    ) or []
    return connections[0] if connections else None


def get_scalar_value(value):
    """递归提取标量值"""
    while isinstance(value, (list, tuple)):
        if len(value) == 0:
            return 0.0
        value = value[0]
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


# 使用示例
if __name__ == "__main__":
    export_arnold_material_to_usd(r"E:/usd/export/v001/mtl31.usda")