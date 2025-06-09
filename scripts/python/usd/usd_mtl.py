# _*_ coding: utf-8 _*_
# .@FileName:usd_mtl
# .@Date....:2025-06-08 : 20 : 32
# .@Aurhor..:冥羽
# .@Contact.:1942598111@qq.com
'''
launch:
        import usd_mtl as Qs_FileName
        reload(FileName)
        FileName.main()
'''
import maya.cmds as cmds
from pxr import Usd, UsdGeom, UsdShade, Gf, Sdf


def export_simple_hierarchy(file_path):
    """仅导出层级结构和材质绑定的简化版本"""
    # 获取当前选中的根节点
    selected_roots = cmds.ls(selection=True, long=True)
    if not selected_roots:
        cmds.warning("请先选中一个或多个根节点")
        return False

    # 创建USD舞台
    stage = Usd.Stage.CreateNew(file_path)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)

    # 设置根Prim
    root_prim = stage.OverridePrim("/Root")
    stage.SetDefaultPrim(root_prim)

    # 创建材质根目录（改为Scope类型）
    materials_root = stage.DefinePrim("/Root/Materials", "Scope")

    # 材质字典（避免重复创建）
    material_dict = {}

    # 导出选中的每个根节点及其子层级
    for root in selected_roots:
        export_node(stage, root, "/Root", material_dict)

    # 保存文件
    stage.GetRootLayer().Save()
    cmds.warning(f"成功导出简化层级到: {file_path}")
    return True


def export_node(stage, maya_node_path, usd_parent_path, material_dict):
    """递归导出节点层级"""
    # 生成合法的USD路径名称
    node_name = maya_node_path.split("|")[-1].replace(":", "_")
    usd_path = f"{usd_parent_path}/{node_name}"

    # 创建Override Prim（不区分类型）
    prim = stage.OverridePrim(usd_path)

    # 如果是mesh节点，处理材质绑定
    if cmds.nodeType(maya_node_path) == "mesh":
        bind_materials(maya_node_path, stage, prim, material_dict)

    # 递归处理子节点
    children = cmds.listRelatives(maya_node_path, children=True, fullPath=True) or []
    for child in children:
        export_node(stage, child, usd_path, material_dict)


def bind_materials(maya_mesh_path, stage, usd_prim, material_dict):
    """绑定材质到Prim"""
    shading_groups = cmds.listConnections(maya_mesh_path, type="shadingEngine") or []
    if not shading_groups:
        return

    for sg in shading_groups:
        materials = cmds.listConnections(sg + ".surfaceShader") or []
        if not materials:
            continue

        material = materials[0]
        material_name = material.replace(":", "_")
        material_path = f"/Root/Materials/{material_name}"

        # 创建材质（如果尚未存在）
        if material_name not in material_dict:
            create_basic_material(stage, material_path, material)
            material_dict[material_name] = material_path

        # 绑定材质
        binding_api = UsdShade.MaterialBindingAPI(usd_prim)
        material_prim = stage.GetPrimAtPath(material_dict[material_name])
        binding_api.Bind(UsdShade.Material(material_prim))


def create_basic_material(stage, material_path, maya_material):
    """创建基础材质"""
    usd_material = UsdShade.Material.Define(stage, material_path)
    shader = UsdShade.Shader.Define(stage, f"{material_path}/Shader")
    shader.CreateIdAttr("UsdPreviewSurface")

    # 基础颜色
    if cmds.attributeQuery("color", node=maya_material, exists=True):
        color = cmds.getAttr(maya_material + ".color")[0]
        shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color))


# 使用示例
export_simple_hierarchy(r"E:\usd\export\v001\mtl26.usda")