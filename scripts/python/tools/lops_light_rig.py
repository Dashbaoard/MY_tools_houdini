# _*_ coding: utf-8 _*_
# .@FileName:lops_light_rig
# .@Date....:2025-05-25 : 01 : 18
# .@Aurhor..:冥羽
# .@Contact.:1942598111@qq.com
'''
launch:
        import lops_light_rig as Qs_FileName
        reload(FileName)
        FileName.main()
'''
import hou
import numpy as np
from tools.modules import misc_utils


def create_three_point_light():
    '''
    Creates a 3 point light setup around a selected object in Solaris
    '''

    # Get the selected nodes and check if we are in Solaris
    selected_node = hou.selectedNodes()
    is_solaris = misc_utils._is_in_solaris()

    if not selected_node or not is_solaris:
        hou.ui.displayMessage(
            "No valid node selected. Please select a node in Solaris",
            severity = hou.severityType.Error
        )
        return False

    target_node = selected_node[0]

    # Get the bounding box for the asset
    bounds = misc_utils.calculate_prim_bounds(target_node)
    print(bounds)

    # Calculate the center and dimensions
    center = bounds["center"]
    size = bounds["size"]
    max_dim = max(size)

    # Calculate the light position
    # Key light
    key_position = hou.Vector3(
        center[0] + max_dim * -1.5,
        center[1] + max_dim * 1.5,
        center[2] + max_dim * 1,
    )

    fill_position = hou.Vector3(
        center[0] + max_dim * 1.5,
        center[1] + max_dim * 1.5,
        center[2] + max_dim * 1,
    )

    back_position = hou.Vector3(
        center[0] - max_dim * 1.5,
        center[1] + max_dim * 1.5,
        center[2] - max_dim * 1,
    )

    # Create the light and extra nodes
    stage = hou.node("/stage")
    key_light = stage.createNode("light::2.0", "key_light")
    fill_light = stage.createNode("light::2.0", "fill_light")
    back_light = stage.createNode("light::2.0", "back_light")

    # Set the light position
    key_light.parmTuple("t").set(key_position)
    fill_light.parmTuple("t").set(fill_position)
    back_light.parmTuple("t").set(back_position)

    # Make the lights look at the center
    for light in [key_light, fill_light, back_light]:
        light.parm("lighttype").set(4)
        light.parm("xn__inputsexposure_vya").set(1)
        light_position = hou.Vector3(light.parmTuple("t").eval())
        light_direction = center - light_position

        # Conver the direction into angles
        x_angle_pitch = np.arctan2(light_direction[1], np.sqrt(light_direction[0]**2 + light_direction[2]**2))
        y_angle_yaw = np.arctan2(-light_direction[0], -light_direction[2])

        # Convert radians to degrees
        light.parmTuple("r").set((np.degrees(x_angle_pitch), np.degrees(y_angle_yaw), 0))

    # Adjust light settings
    # Key light
    key_light.parm("xn__inputsintensity_i0a").set(4)

    # Fill light
    fill_light.parm("xn__inputsintensity_i0a").set(2)
    fill_light.parmTuple("xn__inputscolor_zta").set((0.8, 0.8, 1))

    # Back light
    back_light.parm("xn__inputsintensity_i0a").set(2)
    back_light.parmTuple("xn__inputscolor_zta").set((1, 0.7, 0.7))

    # Support nodes
    xform_light = stage.createNode("xform", "three_point_transform")
    light_mixer = stage.createNode("lightmixer", "three_point_mixer")
    graft_branch = stage.createNode("graftbranches", "three_point_merge")

    # xform to control all lights
    xform_light.parm("primpattern").set("*type:light")

    # Remove graft branch
    graft_branch.parm("srcprimpath1").set("/")

    # Add lights to light mixer using ParamTemplateGroup
    lights_to_mixer = (
        '[' +
        '{"type": "LightItem", "path": "/lights/back_light", "prim_path": "/lights/back_light", "rgb": [55, 55, 55], "controls: ["buttons"], "contents":[]},' +
        '{"type": "LightItem", "path": "/lights/fill_light", "prim_path": "/lights/fill_light", "rgb": [55, 55, 55], "controls: ["buttons"], "contents":[]},' +
        '{"type": "LightItem", "path": "/lights/key_light", "prim_path": "/lights/key_light", "rgb": [55, 55, 55], "controls: ["buttons"], "contents":[]},' +
        ']'
    )

    ptg = light_mixer.parmTemplateGroup()

    settings_folder = hou.FolderParmTemplate(
        name="settings_folder",
        label="Settings",
        folder_type=hou.folderType.Simple
    )

    settings_layout = hou.StringParmTemplate(
        name="setting_layout",
        label="Layout",
        num_components=1
    )

    # Add string to folder first
    settings_folder.addParmTemplate(settings_layout)
    ptg.append(settings_folder)
    # Set paramTemplateGroup
    light_mixer.setParmTemplateGroup(ptg)
    # Set light nodes in order to use the light mixer
    light_mixer.parm("setting_layout").set(lights_to_mixer)

    # Layout nodes
    graft_branch.setInput(0, target_node)
    graft_branch.setInput(1, light_mixer)
    light_mixer.setInput(0, xform_light)
    xform_light.setInput(0, back_light)
    back_light.setInput(0, fill_light)
    fill_light.setInput(0, key_light)

    nodes_to_layout = [key_light, back_light, fill_light, graft_branch, light_mixer, xform_light]
    graft_position = graft_branch.moveToGoodPosition()
    new_position_graft = hou.Vector2(graft_position[0], graft_position[1])
    graft_branch.setPosition(new_position_graft)
    stage.layoutChildren(items=nodes_to_layout)