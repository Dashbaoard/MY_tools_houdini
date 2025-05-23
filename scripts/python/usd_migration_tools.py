import os

import hou


class USDMigrationUtils:
    def __init__(self):
        pass

    def test(self):
        print('Hello')

    def createMainTemplate(self, dir_path):
        print('Executing template structure')

        obj_file = [file for file in os.listdir(dir_path) if file.endswith('.obj')][0]
        print(obj_file)

        # sopCreate lop
        root_path = '/stage'
        sopcreate_lop = hou.node(root_path).createNode('sopcreate', 'asset01')
        sopcreate_lop.parm('enable_partitionattribs').set(0)

        #file sop
        file_sop = hou.node(sopcreate_lop.path() + "/sopnet/create").createNode("file")
        file_sop.parm('file').set(dir_path + '/' + obj_file)

        # for loop
        for_each_begin = file_sop.createOutputNode('block_begin', 'foreach_begin1')
        for_each_begin.parm('method').set(1)
        for_each_begin.parm('blockpath').set('../foreach_end1')
        for_each_begin.parm('createmetablock').pressButton()
        meta_node = hou.node(for_each_begin.parent().path() + '/foreach_begin1_metadata1')
        meta_node.parm('blockpath').set('../foreach_end1')

        # attribute wrangle
        attr_wrangle = for_each_begin.createOutputNode('attribwrangle')
        attr_wrangle.setInput(1, meta_node)
        attr_wrangle.parm('class').set(1)
        attr_wrangle.parm('snippet').set('string assets[] = {"leaves","trunk","twigs","leaves_small"};\ns@path = "/" + assets[detail(1,"iteration")];')

        # end loop
        for_each_end = attr_wrangle.createOutputNode('block_end', 'foreach_end1')
        for_each_end.parm('itermethod').set(1)
        for_each_end.parm('method').set(1)
        for_each_end.parm('class').set(0)
        for_each_end.parm('useattrib').set(1)
        for_each_end.parm('attrib').set('shop_materialpath')
        for_each_end.parm('blockpath').set('../foreach_end1')
        for_each_end.parm('templatepath').set('../foreach_begin1')

        # attrib delete
        att_delete = for_each_end.createOutputNode('attribdelete')
        att_delete.parm('ptdel').set('fbx_rotation fbx_scale fbx_translation')
        att_delete.parm('primdel').set('shop_materialpath MaxHandle name')

        output_sop = att_delete.createOutputNode('output')

        # create primitive lop
        primitive_lop = hou.node(root_path).createNode('primitive')
        primitive_lop.parm('primpath').set('/asset01')
        primitive_lop.parm('primkind').set('component')

        # graft stages
        graft_stages_lop = primitive_lop.createOutputNode('graftstages')
        graft_stages_lop.setNextInput(sopcreate_lop)
        graft_stages_lop.parm('primkind').set('subcomponent')

        # material lop
        materials = ["leaves","trunk","twigs","leaves_small"]
        materiallib_lop = graft_stages_lop.createOutputNode('materiallibrary')
        materiallib_lop.parm('materials').set(len(materials))

        for i, material in enumerate(materials):
            materiallib_lop.parm(f'matnode{i+1}').set(material)
            materiallib_lop.parm(f'matpath{i+1}').set(f'/asset01/materials/{material}_mat')
            materiallib_lop.parm(f'assign{i+1}').set(1)
            materiallib_lop.parm(f'geopath{i+1}').set(f'/asset01/asset01/{material}')

            # set mat network inside
            mat_network = hou.node(materiallib_lop.path()).createNode('subnet', material)

            # texture maps and nodes
            usd_uv_texture = hou.node(mat_network.path()).createNode('usduvtexture::2.0')
            texture_dir_ref = dir_path + '/textures'

            if material == 'leaves':
                texture_map_color = [file for file in os.listdir(texture_dir_ref) if file.endswith('1.jpg')]
            elif material == 'trunk':
                texture_map_color = [file for file in os.listdir(texture_dir_ref) if file.endswith('2.jpg')]
            elif material == 'twigs':
                texture_map_color = [file for file in os.listdir(texture_dir_ref) if file.endswith('3.jpg')]
            elif material == 'leaves_small':
                texture_map_color = [file for file in os.listdir(texture_dir_ref) if file.endswith('4.jpg')]
            print(texture_map_color)
            usd_uv_texture.parm('file').set(texture_dir_ref + '/' + texture_map_color[0])

            mtlsurface = hou.node(mat_network.path()).createNode('mtlxstandard_surface')
            output_ref = hou.node(mat_network.path() + '/suboutput1')

            usd_uv_texture_output = usd_uv_texture.outputIndex('rgb')
            mtlsurface_input = mtlsurface.inputIndex('base_color')
            mtlsurface_output = mtlsurface.outputIndex('out')

            mtlsurface.setInput(mtlsurface_input, usd_uv_texture, usd_uv_texture_output)
            output_ref.setNextInput(mtlsurface, mtlsurface_output)

            mat_network.setMaterialFlag(True)






