# _*_ coding: utf-8 _*_
# .@FileName:lops_asset_builder
# .@Date....:2025-05-23 : 10 : 07
# .@Aurhor..:冥羽
# .@Contact.:1942598111@qq.com
'''
launch:
        import lops_asset_builder as Qs_FileName
        reload(FileName)
        FileName.main()
'''
import hou
import os

import tex_to_mtlx
import random
import colorsys


def create_component_builder(selected_directory = None):
    '''
    Main function to create the component builder based on a provided asset
    '''


    # Get the file
    if selected_directory == None:
        selected_directory = hou.ui.selectFile(title = "Select the file you want to import",
                                              file_type = hou.fileType.Geometry,
                                              multiple_select = False)

    selected_directory = hou.text.expandString(selected_directory)

    try:
        if os.path.exists(selected_directory):

            # Define context
            stage_context = hou.node("/stage")

            # Get the path and filename and the folder with the textures
            path, filename = os.path.split(selected_directory)
            folder_textures = os.path.join(path, "maps").replace(os.sep, "/")
            print(folder_textures)
            # Get asset name and extension
            asset_name = filename.split(".")[0]
            asset_extension = filename.split(".")[-1]

            # Create nodes for the component builder setup
            comp_geo = stage_context.createNode("componentgeometry", f"{asset_name}_geo")
            material_lib = stage_context.createNode("materiallibrary", f"{asset_name}_mtl")
            comp_material = stage_context.createNode("componentmaterial", f"{asset_name}_assign")
            comp_out = stage_context.createNode("componentoutput", asset_name)

            # Set parms
            comp_geo.parm("geovariantname").set(asset_name)
            material_lib.parm("matpathprefix").set("/ASSET/mtl/")
            comp_material.parm("nummaterials").set(0)

            # Create auto assignment for materials
            comp_material_edit = comp_material.node("edit")
            output_node = comp_material_edit.node("output0")
            matspecvexpr_code = """
string matPath = '/ASSET/mtl/';
string shop_materialPath;

// 获取当前图元的 primpath 属性值
string primPath = @primpath;

// 检查 primPath 是否以 /ASSET/geo/render 开头
if (startswith(primPath, "/ASSET/geo/render")) {
    // 获取 shop_materialpath 属性值
    shop_materialPath = usd_primvarelement(0, primPath, "shop_materialpath", @elemnum);

    // 移除左侧的 "/mat/" 前缀
    // shop_materialPath = lstrip(shop_materialPath);

    // 拼接最终的材质路径
    string material = concat(matPath, shop_materialPath);

    // 返回生成的材质路径
    return material;
} else {
    // 如果当前图元不在 /ASSET/geo/render 路径下，返回空字符串或默认值
    return "";
}
            """
            assign_material = comp_material_edit.createNode("assignmaterial", f"{asset_name}_assign")
            assign_material.setParms({
                "primpattern1": "%type:Mesh",
                "matspecmethod1": 2,
                "matspecvexpr1": matspecvexpr_code,
                "bindpurpose1": "full"
            })

            # Connect nodes
            comp_material.setInput(0, comp_geo)
            comp_material.setInput(1, material_lib)
            comp_out.setInput(0, comp_material)
            # Connect the input of assign material node to the first subnet indirect input
            assign_material.setInput(0, comp_material_edit.indirectInputs()[0])
            output_node.setInput(0, assign_material)

            # Nodes to layout
            nodes_to_layout = [comp_geo, material_lib, comp_material, comp_out]
            stage_context.layoutChildren(items=nodes_to_layout)

            # Prepare imported geo
            _prepare_imported_asset(comp_geo, asset_name, asset_extension, path, comp_out)

            # Create the materials using the tex_to_mtlx script
            _create_materials(folder_textures, material_lib)

            # Add network box to organize nodes.
            create_organized_net_note(asset_name, nodes_to_layout)

    except Exception as e:
        hou.ui.displayMessage(f"An error happened: {str(e)}",
                              severity = hou.severityType.Error)

def _prepare_imported_asset(parent, name, extension, path, out_node):
    '''
    Creates the network layout for the default, proxy and sim outputs
    Args:
        parent = node where the file needs to be imported and prepared
        name = asset's name
        extension = if we are working with FBX, ABC, OBJ, etc
        path = path where the asset is located
    Return:
        None
    '''
    try:
        # Get the output nodes - default, proxy and sim
        default_output = parent.node("sopnet/geo/default")
        proxy_output = parent.node("sopnet/geo/proxy")
        sim_output = parent.node("sopnet/geo/simproxy")

        # Set the parent node where the nodes are going to be created
        parent = hou.node(parent.path() + "/sopnet/geo")

        # Create the file node that imports the asset
        file_extensions = ["fbx", "obj", "bgeo", "bgeo.sc"]
        if extension in file_extensions:
            file_import = parent.createNode("file", f"import_{name}")
            parm_name = "file"
        elif extension == "abc":
            file_import = parent.createNode("alembic", f"import_{name}")
            parm_name = "fileName"
        else:
            return

        # Create the main nodes
        match_size = parent.createNode("matchsize", f"matchsize_{name}")
        attrib_wrangler = parent.createNode("attribwrangle", "convert_mat_to_name")
        attrib_delete = parent.createNode("attribdelete", "keep_P_N_UV_NAME")
        remove_points = parent.createNode("add", "remove_points")

        # Set parms for main nodes
        file_import.parm(parm_name).set(f"{path}/{name}.{extension}")

        match_size.setParms({
            "justify_x": 0,
            "justify_y": 1,
            "justify_z": 0
        })

        attrib_wrangler.setParms({
            "class": 1,
            "snippet": 'string material_to_name[] = split(s@shop_materialpath, "/");\ns@name = material_to_name[-1];'
        })

        attrib_delete.setParms({
            "negate": True,
            "ptdel": "N P",
            "vtxdel": "uv",
            "primdel": "name shop_materialpath"
        })

        remove_points.parm("remove").set(True)

        # Connect main nodes
        match_size.setInput(0, file_import)
        attrib_wrangler.setInput(0, match_size)
        attrib_wrangler.bypass(True)
        attrib_delete.setInput(0, attrib_wrangler)
        remove_points.setInput(0, attrib_delete)
        default_output.setInput(0, remove_points)

        # Prepare PROXY setup
        poly_reduce = parent.createNode("polyreduce::2.0", "reduce_to_5")
        attrib_colour = parent.createNode("attribwrangle", "set_color")
        color_node = parent.createNode("color", "unique_color")
        attrib_promote = parent.createNode("attribpromote", "promote_Cd")
        attrib_delete_name = parent.createNode("attribdelete", "delete_asset_name")

        # Set parms for proxy setup
        poly_reduce.parm("percentage").set(5)

        # Custom attribute node using the ParmTemplateGroup() for the attrib_color
        attrib_colour.parm("class").set(1)
        ptg = attrib_colour.parmTemplateGroup()

        new_string = hou.StringParmTemplate(
            name="asset_name",
            label="Asset name",
            num_components=1
        )

        ptg.insertAfter("class", new_string)
        attrib_colour.setParmTemplateGroup(ptg)

        # Need to grab the rootprim from the component output and paste a relative reference
        relative_path = attrib_colour.relativePathTo(out_node)
        expression_parm = f'`chs("{relative_path}/rootprim")`'


        attrib_colour.setParms({
            "asset_name": expression_parm,
            "snippet": 's@asset_name = chs("asset_name");'
        })

        color_node.setParms({
            "class": 1,
            "colortype": 4,
            "rampattribute": "asset_name"
        })

        attrib_promote.setParms({
            "inname": "Cd",
            "inclass": 1,
            "outclass": 0
        })

        attrib_delete_name.parm("primdel").set("asset_name")

        # Connect nodes
        poly_reduce.setInput(0, remove_points)
        attrib_colour.setInput(0, poly_reduce)
        color_node.setInput(0, attrib_colour)
        attrib_promote.setInput(0, color_node)
        attrib_delete_name.setInput(0, attrib_promote)
        proxy_output.setInput(0, attrib_delete_name)

        # Prepare the Sim setup
        python_sop = _create_convex(parent)
        name_sop = parent.createNode("name")
        name_sop.parm("name1").set(f'`chs("{relative_path}/rootprim")`')
        # Connect node
        python_sop.setInput(0, remove_points)
        name_sop.setInput(0, python_sop)
        sim_output.setInput(0, name_sop)

        # Layout all nodes
        parent.layoutChildren()

    except Exception as e:
        hou.ui.displayMessage(f"An error happened: {str(e)}",

                              severity=hou.severityType.Error)

def _create_convex(parent):
    '''
    Creates the tPython SOP node that is used to create a convex hull using Scipy
    Args:
        parent = the component geometry node where the file is imported
    Return:
        Python_sop = is python node we create with this function.
    '''

    # Create the Python SOP node
    python_sop = parent.createNode("python", "convex_hull_setup")

    # Create the extra parms to use
    ptg = python_sop.parmTemplateGroup()

    # Normalize Normals Toggle
    normalize_toggle = hou.ToggleParmTemplate(
        name="normalize",
        label="Normalize",
        default_value=True
    )

    # Invert Normals Toggle
    flip_n_toggle = hou.ToggleParmTemplate(
        name="flip_normal",
        label="Flip Normals",
        default_value=True
    )

    # Simplify Toggle
    simplify_toggle = hou.ToggleParmTemplate(
        name="simplify",
        label="Simplify",
        default_value=False
    )

    # Level of detail slider
    level_detail = hou.FloatParmTemplate(
        name="level_detail",
        label="Level of Detail",
        num_components=1,
        disable_when="{simplify == 0}"
    )

    # Append to node
    ptg.append(normalize_toggle)
    ptg.append(flip_n_toggle)
    ptg.append(simplify_toggle)
    ptg.append(level_detail)

    python_sop.setParmTemplateGroup(ptg)
    code = '''
from tools.modules import convex_hull_utils

node = hou.pwd()
geo = node.geometry()

# Get user parms
normalize_parm = node.parm("normalize").eval()
flip_normal_parm = node.parm("flip_normal").eval()
simplify_parm = node.parm("simplify").eval()
level_detail = node.parm("level_detail").eval()

# Get the points
points = [point.position() for point in geo.points()]
convex_hull_utils.create_convex_hull(geo, points)
'''
    code2 = """
string matPath = '/ASSET/mtl/';
string shop_materialPath;

// 获取当前图元的 primpath 属性值
string primPath = @primpath;

// 检查 primPath 是否以 /ASSET/geo/render 开头
if (startswith(primPath, "/ASSET/geo/render")) {
    // 获取 shop_materialpath 属性值
    shop_materialPath = usd_primvarelement(0, primPath, "shop_materialpath", @elemnum);

    // 移除左侧的 "/mat/" 前缀
    // shop_materialPath = lstrip(shop_materialPath);

    // 拼接最终的材质路径
    string material = concat(matPath, shop_materialPath);

    // 返回生成的材质路径
    return material;
} else {
    // 如果当前图元不在 /ASSET/geo/render 路径下，返回空字符串或默认值
    return "";
}
"""
    python_sop.parm("python").set(code)

    return python_sop

def _create_materials(folder_textures, material_lib):
    """
    Create the material using the tex_to_mtlx_script
    Args:
        folder_textures: = the folder that contains the textures to be used
        material_lib = the material library where the materials will be saved
    Returns:
        None
    """
    try:
        if not os.path.exists(folder_textures):
            hou.ui.displayMessage(
                f"Folder does not exist {folder_textures}",
                severity=hou.severityType.Error
            )
            return False

        # Initialize the texture handle TxFromTlx
        material_handler = tex_to_mtlx.TxToMtlx()

        # Check if the folder contains valid textures
        if material_handler.folder_with_textures(folder_textures):
            # Get the texture details
            texture_list = material_handler.get_texture_details(folder_textures)
            print('--------')
            #print(texture_list)
            if texture_list and isinstance(texture_list, dict):

                # Common data
                common_data = {
                    "mtlTX": False,  # If you want to create TX files set to True
                    "path": material_lib.path(),
                    "node": material_lib,
                    # "folder_path": [folder_textures][0]
                    "folder_path": folder_textures
                }

                # Create materials for each texture set
                for material_name in texture_list:
                    # Fix to provide the correct path
                    path = texture_list[material_name]["path"]

                    if not path.endswith("/"):
                        texture_list[material_name]["path"] = path + "/"

                    create_material = tex_to_mtlx.MtlxMaterial(
                        material_name,
                        **common_data,
                        texture_list=texture_list
                    )

                    create_material.create_materialx()
                hou.ui.displayMessage(f'Created {len(texture_list)} materials in {material_lib.path()}',
                                      severity=hou.severityType.Message)
                return True
            else:
                hou.ui.displayMessage("No valid textures sets found", severity=hou.severityType.Message)
                return False
        else:
            hou.ui.displayMessage("No valid textures sets found", severity=hou.severityType.Message)
            return False

    except Exception as e:
        hou.ui.displayMessage(f"Error creating materials: {str(e)}", severity=hou.severityType)
        return False

def random_color():
    """ Generate random RGB values between 0 and 1"""
    red_color = random.random()
    green_color = random.random()
    blue_color = random.random()

    # Get main colour
    main_colour = hou.Color(red_color, green_color, blue_color)
    # Convert RGB to HSV
    hue, saturation, value = colorsys.rgb_to_hsv(red_color, green_color, blue_color)
    new_saturation = saturation * 0.5
    # Get the secondary colour
    sec_red, sec_green, sec_blue = colorsys.hsv_to_rgb(hue, new_saturation, value)
    secondary_colour = hou.Color(sec_red, sec_green, sec_blue)

    return (main_colour, secondary_colour)

def create_organized_net_note(asset_name, nodes_to_layout):
    """
    Creates a network box organization around selected nodes with a title sticky note
    Args:
        asset_name = Text to display in the sticky note
        nodes_to_layout = list of nodes to be included in the network box
    Return:
        None
    """
    # Get the parent context
    parent = nodes_to_layout[0].parent()

    # Get colours for the network box and sticky note
    background_colour = 0.189
    parent_colour = hou.Color(background_colour, background_colour, background_colour)

    child_colour, sticky_note_colour = random_color()
    text = 0.8
    sticky_note_text = hou.Color(text, text, text)

    # Create the network boxes
    parent_box = parent.createNetworkBox()
    child_box = parent.createNetworkBox()

    # Calculate the node position
    positions = [node.position() for node in nodes_to_layout]
    center_x = sum(pos.x() for pos in positions) / len(positions)
    center_y = sum(pos.y() for pos in positions) / len(positions)
    center = hou.Vector2(center_x, center_y)

    # Position the boxes
    parent_box.setPosition(center)
    child_box.setPosition(center)

    parent_box.addItem(child_box)

    for node in nodes_to_layout:
        child_box.addItem(node)

    child_box.fitAroundContents()

    # Create sticky note
    sticky_note = parent.createStickyNote()
    parent_box.addItem(sticky_note)

    # Get the dimensions for the sticky note based on the child box
    sticky_note_width = child_box.size().x()
    sticky_note_height = 0.75

    sticky_note.setSize(hou.Vector2(sticky_note_width, sticky_note_height))

    # Calculate the position for the sticky note based on the child box position
    child_box_top = child_box.position().y() + (child_box.size().y() / 2)
    sticky_note_x = child_box.position().x()
    sticky_note_y = child_box_top + sticky_note_height * 3

    sticky_note.setPosition(hou.Vector2(sticky_note_x, sticky_note_y))

    # Configure sticky note colour and text
    sticky_note.setText(asset_name)
    sticky_note.setTextSize(0.35)
    sticky_note.setTextColor(sticky_note_text)
    sticky_note.setColor(sticky_note_colour)

    # Configure the network box colour
    parent_box.setComment(asset_name)
    parent_box.setColor(parent_colour)
    child_box.setColor(child_colour)

    # Fit parent box around everything
    parent_box.fitAroundContents()