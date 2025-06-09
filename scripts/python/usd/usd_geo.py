# _*_ coding: utf-8 _*_
# .@FileName:usd_geo
# .@Date....:2025-06-08 : 17 : 07
# .@Aurhor..:冥羽
# .@Contact.:1942598111@qq.com
'''
launch:
        import usd_geo as Qs_FileName
        reload(FileName)
        FileName.main()
'''
import maya.cmds as cmds
from pxr import Usd, UsdGeom, Gf, Sdf, Vt


def export_group_with_hierarchy(file_path):
    # 获取当前选中的组
    selected_groups = cmds.ls(selection=True, long=True)
    if not selected_groups:
        cmds.warning("请先选中一个或多个组")
        return False

    # 创建USD舞台
    stage = Usd.Stage.CreateNew(file_path)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)

    # 设置根Prim
    root_prim = stage.DefinePrim("/Root", "Xform")
    stage.SetDefaultPrim(root_prim)

    # 处理每个选中的组
    for group in selected_groups:
        export_group_contents(stage, group, "/Root")

    # 保存文件
    stage.GetRootLayer().Save()
    cmds.warning("成功导出到: " + file_path)
    return True


def export_group_contents(stage, maya_path, usd_parent_path):
    # 创建对应的USD路径
    node_name = maya_path.split("|")[-1]
    usd_path = usd_parent_path + "/" + node_name.replace(":", "_")

    # 检查是否是变换节点(组)
    if cmds.nodeType(maya_path) == "transform":
        # 创建Xform Prim
        xform_prim = stage.DefinePrim(usd_path, "Xform")

        # 应用变换矩阵
        xform = UsdGeom.Xformable(xform_prim)
        transform = cmds.xform(maya_path, query=True, matrix=True, worldSpace=True)
        xform.AddTransformOp().Set(Gf.Matrix4d(*transform))

        # 递归处理子对象
        children = cmds.listRelatives(maya_path, children=True, fullPath=True) or []
        for child in children:
            export_group_contents(stage, child, usd_path)

    # 处理网格对象
    elif cmds.nodeType(maya_path) == "mesh":
        # 获取变换节点和原始名称
        transform_node = cmds.listRelatives(maya_path, parent=True, fullPath=True)[0]
        mesh_name = cmds.ls(maya_path, long=False)[0]  # 获取mesh的短名称

        # 使用mesh的原始名称创建Prim路径
        usd_path = usd_parent_path + "/" + mesh_name.replace(":", "_")

        # 创建Mesh Prim
        mesh_prim = stage.DefinePrim(usd_path, "Mesh")
        usd_mesh = UsdGeom.Mesh(mesh_prim)

        # 获取顶点数据
        vertices = cmds.getAttr(maya_path + ".vrts[*]")
        points = Vt.Vec3fArray([Gf.Vec3f(v[0], v[1], v[2]) for v in vertices])
        usd_mesh.CreatePointsAttr(points)

        # 获取面数据
        num_faces = cmds.polyEvaluate(maya_path, face=True)
        face_counts = []
        face_indices = []

        for i in range(num_faces):
            face_vertices = cmds.polyInfo(maya_path + ".f[" + str(i) + "]", faceToVertex=True)[0].split()
            face_vertices = [int(v) for v in face_vertices[2:]]
            face_counts.append(len(face_vertices))
            face_indices.extend(face_vertices)

        usd_mesh.CreateFaceVertexCountsAttr(face_counts)
        usd_mesh.CreateFaceVertexIndicesAttr(face_indices)

        # 获取UV数据
        uv_sets = cmds.polyUVSet(maya_path, query=True, allUVSets=True)
        if uv_sets:
            primvars_api = UsdGeom.PrimvarsAPI(mesh_prim)

            for uv_set in uv_sets:
                cmds.polyUVSet(maya_path, currentUVSet=True, uvSet=uv_set)
                num_uvs = cmds.polyEvaluate(maya_path, uvcoord=True)

                uvs = []
                uv_indices = []

                # 获取UV坐标
                for i in range(num_uvs):
                    uv = cmds.polyEditUV(maya_path + ".map[" + str(i) + "]", query=True)
                    uvs.append(Gf.Vec2f(uv[0], uv[1]))

                # 获取UV索引
                for face_id in range(num_faces):
                    uv_ids = cmds.polyInfo(maya_path + ".f[" + str(face_id) + "]")
                    if uv_ids:
                        uv_ids = [int(id) for id in uv_ids[0].split()[2:]]
                        uv_indices.extend(uv_ids)

                # 创建Primvar
                primvar_name = "st" if uv_set == "map1" else uv_set
                primvar = primvars_api.CreatePrimvar(
                    primvar_name,
                    Sdf.ValueTypeNames.TexCoord2fArray,
                    UsdGeom.Tokens.faceVarying
                )
                primvar.Set(uvs)
                if uv_indices:
                    primvar.SetIndices(Vt.IntArray(uv_indices))

        # 应用变换
        xform = UsdGeom.Xformable(mesh_prim)
        transform = cmds.xform(transform_node, query=True, matrix=True, worldSpace=True)
        xform.AddTransformOp().Set(Gf.Matrix4d(*transform))


# 使用示例
export_group_with_hierarchy(r"E:\usd\export\v001\mod22.usda")