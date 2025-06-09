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
    shader.CreateIdAttr("arnold:standard_surface")  # 关键修改：使用Arnold原生节点

    # Arnold 属性映射表（保持原名）
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
        # 更多属性...
    }

    for maya_attr, arnold_attr in attribute_map.items():
        if not cmds.attributeQuery(maya_attr, node=maya_material, exists=True):
            continue

        # 处理纹理连接
        texture_node = get_connected_texture(maya_material, maya_attr)
        if texture_node:
            export_arnold_texture(stage, texture_node, shader, arnold_attr, usd_material_path)
        else:
            # 处理普通属性值
            value = cmds.getAttr(f"{maya_material}.{maya_attr}")
            if isinstance(value, (list, tuple)) and len(value) >= 3:  # 颜色
                shader.CreateInput(arnold_attr, Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*value[:3]))
            else:
                scalar_value = get_scalar_value(value)
                shader.CreateInput(arnold_attr, Sdf.ValueTypeNames.Float).Set(scalar_value)
    # 特殊处理法线贴图
    export_arnold_normal_map(stage, maya_material, shader, usd_material_path)

    usd_material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")


def export_arnold_texture(stage, maya_texture_node, usd_shader, arnold_attr, material_path):
    """导出为 arnold:image 节点"""
    if cmds.nodeType(maya_texture_node) == "file":
        texture_path = cmds.getAttr(f"{maya_texture_node}.fileTextureName")
    else:  # aiImage
        texture_path = cmds.getAttr(f"{maya_texture_node}.filename")

    if not texture_path:
        return

    # 创建 arnold:image 节点（而非 UsdUVTexture）
    texture_name = f"{arnold_attr}_texture"
    texture_shader = UsdShade.Shader.Define(stage, f"{material_path}/{texture_name}")
    texture_shader.CreateIdAttr("arnold:image")  # Arnold原生纹理节点
    texture_shader.CreateInput("filename", Sdf.ValueTypeNames.Asset).Set(texture_path)

    # 连接颜色或单通道
    if arnold_attr.endswith("_color") or arnold_attr == "base_color":
        texture_shader.CreateOutput("out", Sdf.ValueTypeNames.Color3f)
        usd_shader.CreateInput(arnold_attr, Sdf.ValueTypeNames.Color3f).ConnectToSource(
            texture_shader.ConnectableAPI(), "out")
    else:
        texture_shader.CreateOutput("out", Sdf.ValueTypeNames.Float)
        usd_shader.CreateInput(arnold_attr, Sdf.ValueTypeNames.Float).ConnectToSource(
            texture_shader.ConnectableAPI(), "out")


def export_arnold_normal_map(stage, maya_material, usd_shader, material_path):
    """处理 Arnold 法线贴图（使用 arnold:normal_map）"""
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

        texture_path = cmds.getAttr(f"{texture_node}.fileTextureName") if cmds.nodeType(
            texture_node) == "file" else cmds.getAttr(f"{texture_node}.filename")
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
            tex_shader.ConnectableAPI(), "out")

        # 3. 连接到材质的 normal 属性
        usd_shader.CreateInput("normal", Sdf.ValueTypeNames.Vector3f).ConnectToSource(
            normal_shader.ConnectableAPI(), "out")


# 辅助函数保持不变...
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
    """递归提取标量值，处理嵌套列表/元组"""
    while isinstance(value, (list, tuple)):
        if len(value) == 0:
            return 0.0  # 空列表返回0
        value = value[0]  # 提取第一个元素
    # 确保最终值是可转换为浮点数的类型
    try:
        return float(value)
    except (ValueError, TypeError):
        print(f"警告: 无法将值 {value} 转换为浮点数")
        return 0.0


# 使用示例
if __name__ == "__main__":
    export_arnold_material_to_usd(r"C:/gongcheng/maya_usd/asset/v001/mtl10.usda")