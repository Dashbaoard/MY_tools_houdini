import hou
def split_geo():
    # Get the selected node
    selected_node = hou.selectedNodes()

    # Check if the node is selected
    if not selected_node:
        hou.ui.displayMessage('No node is selected')
        raise ValueError('No node is selected')

    selected_node = selected_node[0]
    # Set working context
    parent_node = selected_node.parent()

    geo_info = selected_node.geometry()

    # Request for an attribute
    button_pressed, attribute_name = hou.ui.readInput(
                    "Prvoide the attribute's name to split the geometry",
                    buttons=("OK","Cancel"))


    if button_pressed == 1 or not attribute_name:
        hou.ui.displayMessage("No attribute provided. Try again")
        raise ValueError("No attribute provided. Try again")

    # Check if is valid
    attribute_split = geo_info.findPrimAttrib(attribute_name)

    if not attribute_split:
        hou.ui.displayMessage(f"The specified attribute - {attribute_name} - does not exist")
        raise ValueError(f"The specified attribute - {attribute_name} - does not exist")

    #Get Value
    unique_values = set()

    for prim in geo_info.prims():
        unique_values.add(prim.attribValue(attribute_name))

    # Createing the nodes
    merge_node = parent_node.createNode('merge', "MergeAll")
    nodes_to_layout = [selected_node]

    for index,value in enumerate(unique_values):
        # Create Blast node
        blast_node = parent_node.createNode('blast', attribute_name+"_"+value)
        blast_node.setInput(0, selected_node)
        blast_node.parm('group').set('@name={}'.format(value))
        blast_node.parm('negate').set(True)

        #Create the Null node
        null_node = parent_node.createNode('null', value+'_OUT')
        null_node.setInput(0, blast_node)

        merge_node.setInput(index, null_node)

        # Add nodes to layout list
        nodes_to_layout.extend([blast_node, null_node])

    # Layout nodes
    nodes_to_layout.append(merge_node)
    parent_node.layoutChildren(items=nodes_to_layout)

    merge_node.setDisplayFlag(True)
    merge_node.setRenderFlag(True)