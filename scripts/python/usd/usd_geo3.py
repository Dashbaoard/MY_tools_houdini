# _*_ coding: utf-8 _*_
# .@FileName:usd_geo3
# .@Date....:2025-06-11 : 01 : 12
# .@Aurhor..:冥羽
# .@Contact.:1942598111@qq.com
'''
launch:
        import usd_geo3 as Qs_FileName
        reload(FileName)
        FileName.main()
'''
# _*_ coding: utf-8 _*_
# USD几何体导出工具（支持UV索引精确导出）

import maya.cmds as cmds
import maya.OpenMaya as OpenMaya
from pxr import Usd, UsdGeom, Gf, Sdf, Vt


def get_mesh_uv_indices(maya_mesh):
    """获取Maya网格的UV索引（使用OpenMaya API）"""
    selection = OpenMaya.MSelectionList()
    selection.add(maya_mesh)

    dagPath = OpenMaya.MDagPath()
    component = OpenMaya.MObject()
    selection.getDagPath(0, dagPath, component)

    meshFn = OpenMaya.MFnMesh(dagPath)
    uvSetNames = []
    meshFn.getUVSetNames(uvSetNames)

    if not uvSetNames:
        return None, None

    uvSetName = uvSetNames[0]
    uvCounts = OpenMaya.MIntArray()
    uvIds = OpenMaya.MIntArray()
    meshFn.getAssignedUVs(uvCounts, uvIds, uvSetName)

    # 转换为Python列表
    return [uvIds[i] for i in range(uvIds.length())], uvSetName


def export_mesh_uvs(mesh_prim, maya_mesh):
    """导出UV数据（精确计算st:indices）"""
    # 获取Maya中的UV索引
    uv_indices, uv_set_name = get_mesh_uv_indices(maya_mesh)
    if uv_indices is None:
        return

    # 获取UV坐标
    num_uvs = cmds.polyEvaluate(maya_mesh, uvcoord=True)
    uv_coords = []
    for i in range(num_uvs):
        uv = cmds.polyEditUV(f"{maya_mesh}.map[{i}]", query=True)
        uv_coords.append(Gf.Vec2f(uv[0], uv[1]))

    # 创建Primvar（使用faceVarying插值）
    primvars_api = UsdGeom.PrimvarsAPI(mesh_prim)
    primvar_name = "st" if uv_set_name == "map1" else uv_set_name

    primvar = primvars_api.CreatePrimvar(
        primvar_name,
        Sdf.ValueTypeNames.TexCoord2fArray,
        UsdGeom.Tokens.faceVarying
    )
    primvar.Set(uv_coords)
    primvar.SetIndices(Vt.IntArray(uv_indices))  # 关键：使用Maya的原始UV索引


def export_group_contents(stage, maya_path, usd_parent_path):
    """导出组内容（含UV索引处理）"""
    node_name = maya_path.split("|")[-1].replace(":", "_")
    usd_path = f"{usd_parent_path}/{node_name}"

    if cmds.nodeType(maya_path) == "transform":
        xform_prim = stage.DefinePrim(usd_path, "Xform")
        xform = UsdGeom.Xformable(xform_prim)
        transform = cmds.xform(maya_path, query=True, matrix=True, worldSpace=True)
        xform.AddTransformOp().Set(Gf.Matrix4d(*transform))

        children = cmds.listRelatives(maya_path, children=True, fullPath=True) or []
        for child in children:
            export_group_contents(stage, child, usd_path)

    elif cmds.nodeType(maya_path) == "mesh":
        transform_node = cmds.listRelatives(maya_path, parent=True, fullPath=True)[0]
        usd_path = f"{usd_parent_path}/{node_name}"

        mesh_prim = stage.DefinePrim(usd_path, "Mesh")
        usd_mesh = UsdGeom.Mesh(mesh_prim)

        # 导出顶点和面数据
        vertices = cmds.getAttr(maya_path + ".vrts[*]")
        points = Vt.Vec3fArray([Gf.Vec3f(v[0], v[1], v[2]) for v in vertices])
        usd_mesh.CreatePointsAttr(points)

        num_faces = cmds.polyEvaluate(maya_path, face=True)
        face_counts = []
        face_indices = []
        for i in range(num_faces):
            face_vertices = cmds.polyInfo(f"{maya_path}.f[{i}]", faceToVertex=True)[0].split()
            face_vertices = [int(v) for v in face_vertices[2:]]
            face_counts.append(len(face_vertices))
            face_indices.extend(face_vertices)

        usd_mesh.CreateFaceVertexCountsAttr(face_counts)
        usd_mesh.CreateFaceVertexIndicesAttr(face_indices)

        # 导出UV（带精确索引）
        export_mesh_uvs(mesh_prim, maya_path)

        # 应用变换
        xform = UsdGeom.Xformable(mesh_prim)
        transform = cmds.xform(transform_node, query=True, matrix=True, worldSpace=True)
        xform.AddTransformOp().Set(Gf.Matrix4d(*transform))


def export_group_with_hierarchy(file_path):
    """主导出函数"""
    selected_groups = cmds.ls(selection=True, long=True)
    if not selected_groups:
        cmds.warning("请先选中一个或多个组")
        return False

    stage = Usd.Stage.CreateNew(file_path)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    root_prim = stage.DefinePrim("/Root", "Xform")
    stage.SetDefaultPrim(root_prim)

    for group in selected_groups:
        export_group_contents(stage, group, "/Root")

    stage.GetRootLayer().Save()
    cmds.warning(f"成功导出到: {file_path}")
    return True


# 使用示例
export_group_with_hierarchy(r"E:/usd/export/v002/mod20.usda")