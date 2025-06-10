# _*_ coding: utf-8 _*_
# USD Export with Transform Names Only + Correct st:indices

import maya.cmds as cmds
import maya.OpenMaya as om
from pxr import Usd, UsdGeom, Gf, Sdf, Vt


def get_mesh_uv_indices(maya_mesh):
    """Get UV indices using OpenMaya API for accurate results"""
    selection = om.MSelectionList()
    selection.add(maya_mesh)

    dagPath = om.MDagPath()
    component = om.MObject()
    selection.getDagPath(0, dagPath, component)

    meshFn = om.MFnMesh(dagPath)
    uvSetNames = []
    meshFn.getUVSetNames(uvSetNames)

    if not uvSetNames:
        return None, None

    uvSetName = uvSetNames[0]
    uvCounts = om.MIntArray()
    uvIds = om.MIntArray()
    meshFn.getAssignedUVs(uvCounts, uvIds, uvSetName)

    return [uvIds[i] for i in range(uvIds.length())], uvSetName


def export_merged_transform_shape(file_path):
    """Main export function"""
    selected = cmds.ls(selection=True, long=True)
    if not selected:
        cmds.warning("Please select objects to export")
        return False

    stage = Usd.Stage.CreateNew(file_path)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    root_prim = stage.DefinePrim("/Root", "Xform")
    stage.SetDefaultPrim(root_prim)

    for item in selected:
        process_node(stage, item, "/Root")

    stage.GetRootLayer().Save()
    cmds.warning(f"Successfully exported to: {file_path}")
    return True


def process_node(stage, maya_path, usd_parent_path):
    """Process Maya node hierarchy"""
    node_name = maya_path.split("|")[-1].replace(":", "_")
    usd_path = f"{usd_parent_path}/{node_name}"

    if cmds.getAttr(maya_path + ".intermediateObject"):
        return

    node_type = cmds.nodeType(maya_path)

    if node_type == "transform":
        shapes = cmds.listRelatives(maya_path, shapes=True, fullPath=True) or []

        if not shapes:
            # Empty transform
            stage.DefinePrim(usd_path, "Xform")
            set_transform(stage.GetPrimAtPath(usd_path), maya_path)
        else:
            # Process first valid mesh shape
            for shape in shapes:
                if not cmds.getAttr(shape + ".intermediateObject") and cmds.nodeType(shape) == "mesh":
                    export_mesh(stage, maya_path, shape, usd_path)
                    break

        # Process child transforms
        children = cmds.listRelatives(maya_path, children=True, fullPath=True, type="transform") or []
        for child in children:
            process_node(stage, child, usd_path)

    elif node_type == "mesh":
        # Standalone mesh
        export_mesh(stage, maya_path, maya_path, usd_parent_path)


def export_mesh(stage, transform_path, shape_path, usd_path):
    """Export mesh with transform data and proper UV indices"""
    mesh_prim = stage.DefinePrim(usd_path, "Mesh")
    usd_mesh = UsdGeom.Mesh(mesh_prim)

    # Export core mesh data
    vertices = cmds.getAttr(shape_path + ".vrts[*]")
    points = Vt.Vec3fArray([Gf.Vec3f(v[0], v[1], v[2]) for v in vertices])
    usd_mesh.CreatePointsAttr(points)

    num_faces = cmds.polyEvaluate(shape_path, face=True)
    face_counts = []
    face_indices = []
    for i in range(num_faces):
        face_vertices = cmds.polyInfo(f"{shape_path}.f[{i}]", faceToVertex=True)[0].split()
        face_vertices = [int(v) for v in face_vertices[2:]]
        face_counts.append(len(face_vertices))
        face_indices.extend(face_vertices)

    usd_mesh.CreateFaceVertexCountsAttr(face_counts)
    usd_mesh.CreateFaceVertexIndicesAttr(face_indices)

    # Export UVs with correct indices
    uv_indices, uv_set_name = get_mesh_uv_indices(shape_path)
    if uv_indices:
        export_uvs_with_indices(mesh_prim, shape_path, uv_indices, uv_set_name)

    # Apply transform
    set_transform(mesh_prim, transform_path)


def export_uvs_with_indices(mesh_prim, maya_mesh, uv_indices, uv_set_name):
    """Export UVs with preserved indices"""
    num_uvs = cmds.polyEvaluate(maya_mesh, uvcoord=True)
    uv_coords = []
    for i in range(num_uvs):
        uv = cmds.polyEditUV(f"{maya_mesh}.map[{i}]", query=True)
        uv_coords.append(Gf.Vec2f(uv[0], uv[1]))

    primvars_api = UsdGeom.PrimvarsAPI(mesh_prim)
    primvar_name = "st" if uv_set_name == "map1" else uv_set_name

    primvar = primvars_api.CreatePrimvar(
        primvar_name,
        Sdf.ValueTypeNames.TexCoord2fArray,
        UsdGeom.Tokens.faceVarying
    )
    primvar.Set(uv_coords)
    primvar.SetIndices(Vt.IntArray(uv_indices))  # Critical: preserve original indices


def set_transform(prim, maya_path):
    """Apply transform matrix to prim"""
    xform = UsdGeom.Xformable(prim)
    matrix = cmds.xform(maya_path, query=True, matrix=True, worldSpace=True)
    xform.AddTransformOp().Set(Gf.Matrix4d(*matrix))


# Execute export
export_merged_transform_shape(r"E:\usd\export\model_with_uv_indices.usda")