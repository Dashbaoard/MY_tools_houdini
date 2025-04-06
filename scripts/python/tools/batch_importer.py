import hou
def batch_importer():
    # Declaring Variables
    default_directory = hou.text.expandString("$HIP")
    select_directory = hou.ui.selectFile(start_directory=default_directory,
                                        title='Select the files you want to import',
                                        file_type=hou.fileType.Geometry, multiple_select=True)
    if select_directory:
        select_directory = select_directory.split(';')

        obj = hou.node('/obj')
        geo_node = obj.createNode('geo', node_name = 'tempGeo')
        merge_node = geo_node.createNode('merge', node_name = 'MergeAll')
        add_to_merge = 0

        for item in select_directory:
            item = item.strip()
            asset = item.split('/')
            object = asset[-1].split('.')
            object_name = object[0]
            object_ext = object[-1]


            if object_ext == 'abc':
                new_alembic_loader = geo_node.createNode('alembic', node_name=object_name)
                new_alembic_loader.parm('fileName').set(item)

                unpack_node = geo_node.createNode('unpack', node_name=object_name + '_unpack')
                unpack_node.setInput(0, new_alembic_loader)

                transform_node = geo_node.createNode('xform', node_name=object_name + '_xform')
                transform_node.parm('scale').set(0.01)
                transform_node.setInput(0, unpack_node)

                material_node = geo_node.createNode('material', node_name=object_name + '_mat')
                material_node.setInput(0, transform_node)

            else:
                new_file_loader = geo_node.createNode('file', node_name=object_name)
                new_file_loader.parm('file').set(item)

                transform_node = geo_node.createNode('xform', node_name=object_name + '_xform')
                transform_node.parm('scale').set(0.01)
                transform_node.setInput(0, new_file_loader)

                material_node = geo_node.createNode('material', node_name=object_name + '_mat')
                material_node.setInput(0, transform_node)

            merge_node.setInput(add_to_merge, material_node)
            add_to_merge += 1



        geo_node.layoutChildren()
    else:
        hou.ui.displayMessage('Please, check again, No valid file was selected', buttons=('OK',))


    # File node for FBX and OBJ, BGEO