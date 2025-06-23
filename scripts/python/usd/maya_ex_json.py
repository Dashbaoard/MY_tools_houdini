# _*_ coding: utf-8 _*_
# .@FileName:maya_ex_json
# .@Date....:2025-06-23 : 08 : 32
# .@Aurhor..:冥羽
# .@Contact.:1942598111@qq.com
'''
launch:
        import maya_ex_json as Qs_FileName
        reload(FileName)
        FileName.main()
'''
import maya.cmds as cmds
import json
import os
from collections import OrderedDict


def get_selected_objects_materials():
    """获取选定对象关联的所有材质"""
    selected_objects = cmds.ls(selection=True, long=True) or []
    if not selected_objects:
        cmds.warning("请先选择要导出材质的对象")
        return []

    materials = set()

    for obj in selected_objects:
        # 获取对象的形状节点
        shapes = cmds.listRelatives(obj, shapes=True, fullPath=True) or []

        for shape in shapes:
            # 获取连接到形状的着色引擎
            shading_engines = cmds.listConnections(shape, type='shadingEngine') or []

            for shading_engine in shading_engines:
                # 获取连接到着色引擎的材质
                connected_materials = cmds.listConnections(shading_engine + '.surfaceShader') or []
                materials.update(connected_materials)

    return list(materials)


def get_material_details(material):
    """获取材质的详细信息"""
    material_type = cmds.nodeType(material)
    details = {
        'name': material,
        'type': material_type,
        'attributes': OrderedDict(),
        'connections': OrderedDict(),
        'assigned_to': []
    }

    # 获取所有可读属性
    all_attrs = cmds.listAttr(material, read=True, visible=True) or []

    # 对于Arnold材质，添加用户自定义属性
    if material_type.startswith('ai'):
        all_attrs.extend(cmds.listAttr(material, userDefined=True) or [])

    for attr in all_attrs:
        # 跳过常见无用属性
        if attr in ['caching', 'frozen', 'isHistoricallyInteresting', 'nodeState']:
            continue

        full_attr = f"{material}.{attr}"

        # 检查是否有输入连接
        connections = cmds.listConnections(full_attr,
                                           source=True,
                                           destination=False,
                                           plugs=True,
                                           connections=True) or []

        if connections:
            # 有连接，获取连接信息
            connection_info = []
            for i in range(0, len(connections), 2):
                dest_attr = connections[i]  # 材质属性
                src_attr = connections[i + 1]  # 连接的源属性

                # 获取连接的节点信息
                src_node = src_attr.split('.')[0]
                src_node_type = cmds.nodeType(src_node)

                # 获取节点属性
                node_attrs = OrderedDict()
                try:
                    node_attr_list = cmds.listAttr(src_node, readable=True, visible=True) or []
                    for node_attr in node_attr_list:
                        try:
                            # 跳过常见无用属性
                            if node_attr in ['caching', 'frozen', 'isHistoricallyInteresting', 'nodeState']:
                                continue

                            value = cmds.getAttr(f"{src_node}.{node_attr}")
                            if isinstance(value, (list, tuple)) and len(value) == 3:
                                value = list(value)  # 转换颜色值
                            node_attrs[node_attr] = value
                        except:
                            pass
                except:
                    pass

                # 记录节点信息
                node_info = {
                    'node': src_node,
                    'type': src_node_type,
                    'attributes': node_attrs,
                    'source_attribute': src_attr,
                    'target_attribute': dest_attr
                }

                # 如果是文件纹理节点，添加文件路径
                if src_node_type == 'file' and 'fileTextureName' in node_attrs:
                    node_info['file_path'] = node_attrs['fileTextureName']

                connection_info.append(node_info)

            details['connections'][attr] = connection_info
        else:
            # 没有连接，获取属性值
            try:
                value = cmds.getAttr(full_attr)
                if isinstance(value, (list, tuple)) and len(value) == 3:
                    value = list(value)  # 转换颜色值
                details['attributes'][attr] = value
            except:
                pass

    return details


def get_assigned_objects(material):
    """获取使用该材质的对象"""
    assigned_objects = []

    # 获取连接到材质的着色引擎
    shading_engines = cmds.listConnections(material, type='shadingEngine') or []

    for shading_engine in shading_engines:
        # 获取连接到着色引擎的几何体
        geometries = cmds.listConnections(shading_engine + '.dagSetMembers') or []
        assigned_objects.extend(geometries)

    # 去重
    return list(set(assigned_objects))


def export_materials_to_json(file_path=None):
    """导出选定对象的材质信息到JSON文件"""
    # 获取材质列表
    materials = get_selected_objects_materials()
    if not materials:
        cmds.warning("所选对象没有关联的材质")
        return False

    # 收集所有材质详细信息
    materials_data = OrderedDict()

    for material in materials:
        material_details = get_material_details(material)
        material_details['assigned_to'] = get_assigned_objects(material)
        materials_data[material] = material_details

    # 如果没有指定文件路径，弹出保存对话框
    if not file_path:
        file_path = cmds.fileDialog2(
            fileFilter="JSON Files (*.json);;All Files (*.*)",
            dialogStyle=2,
            fileMode=0,
            caption="导出材质为JSON"
        )
        if not file_path:
            return False
        file_path = file_path[0]

    # 确保文件扩展名是.json
    if not file_path.lower().endswith('.json'):
        file_path += '.json'

    # 写入JSON文件
    try:
        with open(file_path, 'w') as f:
            json.dump(materials_data, f, indent=4)
        cmds.warning(f"成功导出 {len(materials)} 个材质到: {file_path}")
        return True
    except Exception as e:
        cmds.warning(f"导出失败: {str(e)}")
        return False


# 创建Maya菜单项
def create_export_menu():
    """创建导出材质的菜单项"""
    if cmds.menu('ExportMaterialMenu', exists=True):
        cmds.deleteUI('ExportMaterialMenu')

    cmds.menu('ExportMaterialMenu', label='材质导出', parent='MayaWindow')
    cmds.menuItem(label='导出材质为JSON', command='export_materials_to_json()')


# 创建菜单
create_export_menu()