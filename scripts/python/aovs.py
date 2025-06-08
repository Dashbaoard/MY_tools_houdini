# _*_ coding: utf-8 _*_
# .@FileName:aovs
# .@Date....:2025-06-07 : 19 : 27
# .@Aurhor..:冥羽
# .@Contact.:1942598111@qq.com
'''
launch:
        import aovs as Qs_FileName
        reload(FileName)
        FileName.main()
'''
import hou
from pxr import Sdf
from pxr import UsdRender
from pxr import UsdShade
import os
import htoa.lop as lop

node = hou.pwd()
stage = node.editableStage()
from itertools import islice

renderproduct_path = '/Render/Products'

stage.DefinePrim('/Render', 'Scope')
stage.DefinePrim(renderproduct_path, 'Scope')
stage.DefinePrim(renderproduct_path + '/Vars', 'Scope')

aov_shader_name = hou.parm('../aov_shader_name').eval()

bty_dict = {
    'diffuse': 'C<RD>.*L',
    'direct_diffuse': 'C<RD>L',
    'indirect_diffuse': 'C<RD>[DSVOB].*L',
    'specular': "C<RS[^'coat''sheen']>.*L",
    'direct_specular': "C<RS[^'coat''sheen']>L",
    'indirect_specular': "C<RS[^'coat''sheen']>[DSVOB].*L",
    'transmission': 'C<TS>.*L',
    'direct_transmission': 'C<TS>L',
    'indirect_transmission': 'C<TS>[DSVOB].*L',
    'sss': 'C<TD>.*L',
    'direct_sss': 'C<TD>L',
    'indirect_sss': 'C<TD>[DSVOB].*L',
}

basic_dict = {
    'volume': 'CV.*L',
    'emission': 'C[LO]',
    'coat': "C<RS'coat'>.*L",
    'sheen': "C<RS'sheen'>.*L",
    'albedo': 'C[DSV]A',
    'diffuse_albedo': 'C<RD>A',
    'direct': 'C[DSV]L',
    'indirect': 'C[DSV][DSVOB].*L',
    'shadow_matte': 'shadow_matte',
    'background': 'CB',
}


def set_rgba():
    prim_var = stage.DefinePrim(renderproduct_path + '/Vars/rgba', 'RenderVar')
    filter = prim_var.CreateAttribute('arnold:filter', Sdf.ValueTypeNames.String)
    filter.Set('gaussian_filter')
    attrib_datatype = prim_var.GetAttribute("dataType")
    attrib_datatype.Set("color4f")
    attrib_sourcetype = prim_var.GetAttribute("sourceType")
    attrib_sourcetype.Set("lpe")
    attrib_sourcename = prim_var.GetAttribute("sourceName")
    attrib_sourcename.Set('C.*')
    attrib_name = prim_var.CreateAttribute('driver:parameters:aov:name', Sdf.ValueTypeNames.String)
    attrib_name.Set('rgba')
    attrib_chan_format = prim_var.CreateAttribute('driver:parameters:aov:format', Sdf.ValueTypeNames.Token)
    attrib_chan_format.Set("color4h")


def set_lpe(lpe_name, lpe_code):
    prim_var = stage.DefinePrim(renderproduct_path + '/Vars/' + lpe_name, 'RenderVar')
    filter = prim_var.CreateAttribute('arnold:filter', Sdf.ValueTypeNames.String)
    filter.Set('gaussian_filter')
    attrib_datatype = prim_var.GetAttribute("dataType")
    attrib_datatype.Set("color3f")
    attrib_sourcetype = prim_var.GetAttribute("sourceType")
    attrib_sourcetype.Set("lpe")
    attrib_sourcename = prim_var.GetAttribute("sourceName")
    attrib_sourcename.Set(lpe_code)
    attrib_name = prim_var.CreateAttribute('driver:parameters:aov:name', Sdf.ValueTypeNames.String)
    attrib_name.Set(lpe_name)
    attrib_chan_format = prim_var.CreateAttribute('driver:parameters:aov:format', Sdf.ValueTypeNames.Token)
    attrib_chan_format.Set("color3h")

    if hou.node("..").parm('merage_aov').eval():
        attrib_chan_prefix = prim_var.CreateAttribute('driver:parameters:aov:channel_prefix', Sdf.ValueTypeNames.String)
        attrib_chan_prefix.Set(lpe_name)


def get_lgt_group():
    lgt_groups = []
    for prim in stage.Traverse():
        if "Light" not in prim.GetTypeName():
            continue
        lgt_name = prim.GetName()
        if prim.GetAttribute("primvars:arnold:aov"):
            lgt_group = prim.GetAttribute("primvars:arnold:aov").Get()
            lgt_groups.append(lgt_group)
    lgt_groups = list(set(lgt_groups))

    return lgt_groups


def set_lgt_lpe(lpe_name, lpe_code):
    lgt_groups = get_lgt_group()
    for grp in lgt_groups:
        lightGrpExp = "<L.'" + grp + "'>"
        prim_var = stage.DefinePrim(renderproduct_path + '/Vars/lgt_' + grp + '_' + lpe_name, 'RenderVar')
        filter = prim_var.CreateAttribute('arnold:filter', Sdf.ValueTypeNames.String)
        filter.Set('gaussian_filter')
        attrib_datatype = prim_var.GetAttribute("dataType")
        attrib_datatype.Set("color3f")
        attrib_sourcetype = prim_var.GetAttribute("sourceType")
        attrib_sourcetype.Set("lpe")
        attrib_sourcename = prim_var.GetAttribute("sourceName")
        attrib_sourcename.Set(lpe_code.replace('L', '') + lightGrpExp)
        attrib_name = prim_var.CreateAttribute('driver:parameters:aov:name', Sdf.ValueTypeNames.String)
        attrib_name.Set('lgt_' + grp + '_' + lpe_name)
        attrib_chan_format = prim_var.CreateAttribute('driver:parameters:aov:format', Sdf.ValueTypeNames.Token)
        attrib_chan_format.Set("color3h")
        if hou.node("..").parm('merage_aov').eval():
            attrib_chan_prefix = prim_var.CreateAttribute('driver:parameters:aov:channel_prefix',
                                                          Sdf.ValueTypeNames.String)
            attrib_chan_prefix.Set('lgt_' + grp + '_' + lpe_name)


for key, value in basic_dict.items():
    if not hou.node("..").parm(key).eval():
        continue
    set_lpe(key, value)
set_rgba()

for key, value in bty_dict.items():
    if not hou.node("..").parm(key).eval():
        continue
    if hou.node("..").parm('lights_group').eval():
        set_lgt_lpe(key, value)
    else:
        set_lpe(key, value)

rendervars = [
    {
        "name": "uv",
        "data_type": "color3f",
        "source_name": "st",
        "source_type": "primvar",
        "format": "float3",
        "filter": "gaussian_filter",
    },

    {
        "name": "AO",
        "data_type": "color3f",
        "source_name": "AO",
        "source_type": "raw",
        "format": "color3f",
        "filter": "gaussian_filter",
    },

    {
        "name": "N",
        "data_type": "color3f",
        "source_name": "N",
        "source_type": "raw",
        "format": "color3f",
        "filter": "closest_filter",
    },

    {
        "name": "P",
        "data_type": "color3f",
        "source_name": "P",
        "source_type": "raw",
        "format": "color3f",
        "filter": "closest_filter",
    },

    {
        "name": "Z",
        "data_type": "color3f",
        "source_name": "Z",
        "source_type": "raw",
        "format": "color3f",
        "filter": "closest_filter",
    },

    {
        "name": "motionvector",
        "data_type": "color3f",
        "source_name": "motionvector",
        "source_type": "raw",
        "format": "color3f",
        "filter": "gaussian_filter",
    },
]


def creat_unint(data_type, source_type, source_name, name, format, filter):
    prim_var = stage.DefinePrim(renderproduct_path + '/Vars/' + rendervar['name'], 'RenderVar')

    attr_filter = prim_var.CreateAttribute('arnold:filter', Sdf.ValueTypeNames.String)
    attr_filter.Set(filter)

    attrib_datatype = prim_var.GetAttribute("dataType")
    attrib_datatype.Set(data_type)

    attrib_sourcetype = prim_var.GetAttribute("sourceType")
    attrib_sourcetype.Set(source_type)

    attrib_sourcename = prim_var.GetAttribute("sourceName")
    attrib_sourcename.Set(source_name)

    attrib_name = prim_var.CreateAttribute('driver:parameters:aov:name', Sdf.ValueTypeNames.String)
    attrib_name.Set(name)

    attrib_chan_format = prim_var.CreateAttribute('driver:parameters:aov:format', Sdf.ValueTypeNames.Token)
    attrib_chan_format.Set(format)

    if hou.node("..").parm('merage_aov').eval():
        attrib_chan_prefix = prim_var.CreateAttribute('driver:parameters:aov:channel_prefix', Sdf.ValueTypeNames.String)
        attrib_chan_prefix.Set(name)


for rendervar in rendervars:
    if not hou.node("..").parm(rendervar['name']).eval():
        continue
    creat_unint(rendervar['data_type'], rendervar['source_type'], rendervar['source_name'], rendervar['name'],
                rendervar['format'], rendervar['filter'])


def chunk(it, size):
    it = iter(it)
    return iter(lambda: tuple(islice(it, size)), ())


# Label, datatype per arnold aovs
aovs_infos = lop.getAovInfoDict()

# Get the values of the multiparm block
aov_list = hou.parm("aovlist")
aov_list.eval()

aovs = list(chunk(aov_list.multiParmInstances(), 6))

prim_paths = lop.computeUniquePrimPaths([name.eval() for name, _, _, _, _, _ in aovs])

for aov, prim_path in zip(aovs, prim_paths):
    name, layer, filter_, precision, light_path, shader = aov
    # print(int(str(name)[17])+7)
    if name.eval():
        # print(light_path)
        if light_path.eval() and shader.eval():
            raise ValueError(f"Error: Both 'light_path' and 'shader' exist for AOV '{name.eval()}'.")
        if light_path.eval():

            prim = stage.DefinePrim(prim_path, "RenderVar")
            prim.GetAttribute("sourceName").Set(light_path.eval())
            prim.GetAttribute("sourceType").Set("lpe")

            layer_name = layer.eval() if layer.eval() else prim.GetName()
            prim.CreateAttribute("driver:parameters:aov:name", Sdf.ValueTypeNames.String).Set(name.eval())

            prim.CreateAttribute("driver:parameters:aov:format", Sdf.ValueTypeNames.Token).Set("color3h")
            prim.GetAttribute("dataType").Set("color3f")
            prim.CreateAttribute("arnold:filter", Sdf.ValueTypeNames.String).Set(filter_.eval())

        elif shader.eval():
            prim = stage.DefinePrim(prim_path, "RenderVar")
            prim.GetAttribute("sourceName").Set(name.eval())
            prim.GetAttribute("sourceType").Set("raw")

            layer_name = layer.eval() if layer.eval() else prim.GetName()
            prim.CreateAttribute("driver:parameters:aov:name", Sdf.ValueTypeNames.String).Set(name.eval())

            prim.CreateAttribute("driver:parameters:aov:format", Sdf.ValueTypeNames.Token).Set("color3f")
            prim.GetAttribute("dataType").Set("color3f")
            prim.CreateAttribute("arnold:filter", Sdf.ValueTypeNames.String).Set(filter_.eval())

            nodeGraph = stage.DefinePrim(aov_shader_name, 'ArnoldNodeGraph')
            aov_ao_nodeGraphTerminal = nodeGraph.CreateAttribute(f'outputs:aov_shaders:i{int(str(name)[17]) + 10}',
                                                                 Sdf.ValueTypeNames.Token)
            aov_ao_nodeGraphTerminal.AddConnection('{}.outputs:shader'.format(shader.eval()))

        else:
            prim = stage.DefinePrim(prim_path, "RenderVar")
            prim.GetAttribute("sourceName").Set(name.eval())
            prim.GetAttribute("sourceType").Set("raw")

            # layer_name = layer.eval() if layer.eval() else prim.GetName()
            # prim.CreateAttribute("driver:parameters:aov:name", Sdf.ValueTypeNames.String).Set(name.eval())

            # prim.CreateAttribute("driver:parameters:aov:format", Sdf.ValueTypeNames.Token).Set("color3f")
            # prim.GetAttribute("dataType").Set("color3f")
            # prim.CreateAttribute("arnold:filter", Sdf.ValueTypeNames.String).Set(filter_.eval())
            layer_name = layer.eval() if layer.eval() else prim.GetName()
            prim.CreateAttribute("driver:parameters:aov:name", Sdf.ValueTypeNames.String).Set(layer_name)

            label, data_type = aovs_infos[name.eval()]
            if precision.eval() == "16":
                aov_format = lop.ArnoldAov.FORMAT_HALF[data_type]
            else:
                aov_format = lop.ArnoldAov.FORMAT_DICT[data_type]
            prim.CreateAttribute("driver:parameters:aov:format", Sdf.ValueTypeNames.Token).Set(aov_format)
            prim.GetAttribute("dataType").Set(lop.ArnoldAov.DATA_TYPE[data_type])
            prim.CreateAttribute("arnold:filter", Sdf.ValueTypeNames.String).Set(filter_.eval())
            # label, data_type = aovs_infos[name.eval()]
            # if precision.eval() == "16":
            #     aov_format = lop.ArnoldAov.FORMAT_HALF[data_type]
            # else:
            #     aov_format = lop.ArnoldAov.FORMAT_DICT[data_type]
            # prim.CreateAttribute("driver:parameters:aov:format", Sdf.ValueTypeNames.Token).Set(aov_format)
            # prim.GetAttribute("dataType").Set(lop.ArnoldAov.DATA_TYPE[data_type])
            # prim.CreateAttribute("arnold:filter", Sdf.ValueTypeNames.String).Set(filter_.eval())

# cryptomatte
use_crypto = hou.parm('../Use_Cryptomatte').eval()
crypto_namespace = hou.parm('../namespace').eval()
do_crypto_object = hou.parm('../crypto_object').eval()
do_crypto_asset = hou.parm('../crypto_asset').eval()

do_crypto_material = hou.parm('../crypto_material').eval()
do_sidecar_manifests = hou.parm('../sidecar_manifests').eval()
depth = hou.parm('../depth').eval()
aov_shader_name = hou.parm('../aov_shader_name').eval()


def CreateRenderVar(aov):
    path = '{}/{}'.format(crypto_namespace, aov)
    renderVar = UsdRender.Var.Define(stage, path)
    renderVar.CreateDataTypeAttr('color3f')
    renderVar.CreateSourceNameAttr(aov)
    renderVar.CreateSourceTypeAttr('raw')
    renderVarPrim = renderVar.GetPrim()
    noopAttr = renderVarPrim.CreateAttribute('arnold:cryptomatte_filter:noop', Sdf.ValueTypeNames.Bool)
    noopAttr.Set(True)
    filterAttr = renderVarPrim.CreateAttribute('arnold:filter', Sdf.ValueTypeNames.String)
    filterAttr.Set('cryptomatte_filter')
    aovNameAttr = renderVarPrim.CreateAttribute('driver:parameters:aov:name', Sdf.ValueTypeNames.String)
    aovNameAttr.Set(aov)

    attrib_chan_prefix = renderVarPrim.CreateAttribute('driver:parameters:aov:attrib_chan_prefix',
                                                       Sdf.ValueTypeNames.String)
    attrib_chan_prefix.Set(aov)


def CreateDepthRenderVar(aov, rank):
    path = '{}/{}'.format(crypto_namespace, aov)
    aovRankStr = '{}'.format(rank)
    if len(aovRankStr) == 1:
        aovRankStr = '0{}'.format(aovRankStr)
    aovPath = '{}{}'.format(path, aovRankStr)
    aovName = '{}{}'.format(aov, aovRankStr)
    renderVar = UsdRender.Var.Define(stage, aovPath)
    renderVar.CreateDataTypeAttr('color4f')
    renderVar.CreateSourceNameAttr(aovName)
    renderVar.CreateSourceTypeAttr('raw')
    renderVarPrim = renderVar.GetPrim()
    filterAttr = renderVarPrim.CreateAttribute('arnold:filter', Sdf.ValueTypeNames.String)
    filterAttr.Set('cryptomatte_filter')
    cryptoFilterAttr = renderVarPrim.CreateAttribute('arnold:cryptomatte_filter:filter', Sdf.ValueTypeNames.String)
    cryptoFilterAttr.Set('gaussian')
    filterRank = renderVarPrim.CreateAttribute('arnold:cryptomatte_filter:rank', Sdf.ValueTypeNames.Int)
    filterRank.Set(rank * 2)
    cryptoFilterName = renderVarPrim.CreateAttribute('arnold:cryptomatte_filter:name', Sdf.ValueTypeNames.String)
    cryptoFilterName.Set('{}_filter{}'.format(aov, aovRankStr))
    aovNameAttr = renderVarPrim.CreateAttribute('driver:parameters:aov:name', Sdf.ValueTypeNames.String)
    aovNameAttr.Set(aovName)
    driverAovFormat = renderVarPrim.CreateAttribute('arnold:format', Sdf.ValueTypeNames.Token)
    driverAovFormat.Set("float")

    attrib_chan_prefix = renderVarPrim.CreateAttribute('driver:parameters:aov:attrib_chan_prefix',
                                                       Sdf.ValueTypeNames.String)
    attrib_chan_prefix.Set(aovName)


depthCount = int(depth / 2)
if use_crypto:
    if do_crypto_asset:
        CreateRenderVar('crypto_asset')
        for i in range(depthCount):
            CreateDepthRenderVar('crypto_asset', i)

    if do_crypto_object:
        CreateRenderVar('crypto_object')
        for i in range(depthCount):
            CreateDepthRenderVar('crypto_object', i)

    if do_crypto_material:
        CreateRenderVar('crypto_material')
        for i in range(depthCount):
            CreateDepthRenderVar('crypto_material', i)

    # Create the cryptomatte shader
    crypto_shader_name = '{}/cryptomatte_shader'.format(aov_shader_name)
    crypto_shader = UsdShade.Shader.Define(stage, crypto_shader_name)
    crypto_shader.CreateOutput('shader', Sdf.ValueTypeNames.Token)
    crypto_shader.CreateIdAttr('arnold:cryptomatte')
    crypto_shader.CreateInput('aov_crypto_asset', Sdf.ValueTypeNames.String).Set('crypto_asset')
    crypto_shader.CreateInput('aov_crypto_object', Sdf.ValueTypeNames.String).Set('crypto_object')
    crypto_shader.CreateInput('aov_crypto_material', Sdf.ValueTypeNames.String).Set('crypto_material')
    crypto_shader.CreateInput('create_depth_outputs', Sdf.ValueTypeNames.Bool).Set(False)
    crypto_shader.CreateInput('custom_output_driver', Sdf.ValueTypeNames.Bool).Set(True)
    crypto_shader.CreateInput('cryptomatte_depth', Sdf.ValueTypeNames.Int).Set(depth)
    crypto_shader.CreateInput('sidecar_manifests', Sdf.ValueTypeNames.Bool).Set(do_sidecar_manifests)

    # Create the Arnold nodegraph
    nodeGraph = stage.DefinePrim(aov_shader_name, 'ArnoldNodeGraph')
    nodeGraphTerminal = nodeGraph.CreateAttribute('outputs:aov_shaders:i1', Sdf.ValueTypeNames.Token)
    nodeGraphTerminal.AddConnection('{}.outputs:shader'.format(crypto_shader_name))

ao = hou.parm('../AO').eval()
if ao:
    whiter = hou.parm('../whiter').eval()
    whiteg = hou.parm('../whiteg').eval()
    whiteb = hou.parm('../whiteb').eval()
    blackr = hou.parm('../blackr').eval()
    blackg = hou.parm('../blackg').eval()
    blackb = hou.parm('../blackb').eval()
    samples = hou.parm('../samples').eval()
    spread = hou.parm('../spread').eval()
    near_clip = hou.parm('../near_clip').eval()
    far_clip = hou.parm('../far_clip').eval()
    falloff = hou.parm('../falloff').eval()
    invert_normals = hou.parm('../invert_normals').eval()
    normalx = hou.parm('../normalx').eval()
    normaly = hou.parm('../normaly').eval()
    normalz = hou.parm('../normalz').eval()
    trace_set = hou.parm('../trace_set').eval()
    inclusive = hou.parm('../inclusive').eval()
    self_only = hou.parm('../self_only').eval()

    ao_shader_name = '{}/ao_shader'.format(aov_shader_name)
    ao_shader = UsdShade.Shader.Define(stage, ao_shader_name)
    ao_shader.CreateIdAttr('arnold:ambient_occlusion')
    ao_shader.CreateInput('black', Sdf.ValueTypeNames.Color3f).Set((blackr, blackg, blackb))
    ao_shader.CreateInput('falloff', Sdf.ValueTypeNames.Float).Set(falloff)
    ao_shader.CreateInput('far_clip', Sdf.ValueTypeNames.Float).Set(far_clip)
    ao_shader.CreateInput('inclusive', Sdf.ValueTypeNames.Bool).Set(inclusive)
    ao_shader.CreateInput('invert_normals', Sdf.ValueTypeNames.Bool).Set(invert_normals)
    ao_shader.CreateInput('near_clip', Sdf.ValueTypeNames.Float).Set(near_clip)
    ao_shader.CreateInput('normal', Sdf.ValueTypeNames.Normal3f).Set((normalx, normaly, normalz))
    ao_shader.CreateInput('samples', Sdf.ValueTypeNames.Int).Set(samples)
    ao_shader.CreateInput('self_only', Sdf.ValueTypeNames.Bool).Set(self_only)
    ao_shader.CreateInput('spread', Sdf.ValueTypeNames.Float).Set(spread)
    ao_shader.CreateInput('trace_set', Sdf.ValueTypeNames.String).Set(trace_set)
    ao_shader.CreateInput('white', Sdf.ValueTypeNames.Color3f).Set((whiter, whiteg, whiteb))
    ao_shader.CreateOutput('rgb', Sdf.ValueTypeNames.Token)

    aov_ao_shader_name = '{}/aov_write_ao_shader'.format(aov_shader_name)
    aov_ao_shader = UsdShade.Shader.Define(stage, aov_ao_shader_name)
    aov_ao_shader.CreateOutput('shader', Sdf.ValueTypeNames.Token)
    aov_ao_shader.CreateIdAttr('arnold:aov_write_rgb')
    aov_ao_input = aov_ao_shader.CreateInput('aov_input', Sdf.ValueTypeNames.Float)
    aov_ao_input.ConnectToSource(ao_shader.GetOutput('rgb'))
    aov_ao_shader.CreateInput('aov_name', Sdf.ValueTypeNames.String).Set('AO')
    aov_ao_shader.CreateInput('blend_opacity', Sdf.ValueTypeNames.Bool).Set(True)
    aov_ao_shader.CreateInput('passthrough', Sdf.ValueTypeNames.String).Set('')

    aov_ao_shader_out = '{}/OUT_material'.format(aov_shader_name)

    nodeGraph = stage.DefinePrim(aov_shader_name, 'ArnoldNodeGraph')
    aov_ao_nodeGraphTerminal = nodeGraph.CreateAttribute('outputs:aov_shaders:i2', Sdf.ValueTypeNames.Token)
    aov_ao_nodeGraphTerminal.AddConnection('{}.outputs:shader'.format(aov_ao_shader_name))


def get_root():
    filename = hou.hipFile.path()

    try:
        project, sequence, shot, d, step, task = filename.split('/')[1:7]

        drive = hou.parm("../drive").eval()

        parent_node = hou.node(".").parent()

        parent_node_name = parent_node.name()

        version = hou.parm("../version").eval()

        version_str = "v{:03d}".format(version)

        path = f'{drive}/{project}/renders/{sequence}/{shot}/3d/{step}/{parent_node_name}/{version_str}'

        if task == 'env':
            path = f'{drive}/{project}/renders/{sequence}/{shot}/3d/{task}/{parent_node_name}/{version_str}'

        name = f'{project}_{sequence}_{shot}'

        return (path, name)

    except (IndexError, ValueError):

        return ('$HIP', '$OS')


def find_render_vars(prim, list_mama):
    """
    递归查找指定原语及其子原语中的所有 UsdRender.Var 类型的原语路径
    :param prim: 当前原语
    :param render_var_paths: 用于存储找到的 RenderVar 路径的列表
    """
    for child_prim in prim.GetChildren():
        # 如果是 RenderVar 类型，添加其路径
        if child_prim.IsA(UsdRender.Var):
            list_mama.append(child_prim.GetPath().pathString)
        # 如果是文件夹（Xform 类型），继续递归查找
        else:
            find_render_vars(child_prim, list_mama)


def create_renderproduct():
    global list_mama

    stage.DefinePrim(renderproduct_path + '/renderproduct', 'Scope')

    parent_node = hou.node(".").parent()
    file_name = hou.parm("../File_Name")

    version = hou.parm("../version").eval()

    version_str = "v{:03d}".format(version)

    format = hou.parm("../format").menuItems()[hou.parm("../format").eval()]

    ProductType = hou.parm("../Product_Type").menuItems()[hou.parm("../Product_Type").eval()]

    path, name = get_root()

    prim = stage.GetPrimAtPath(renderproduct_path + "/Vars")

    list_mama = []
    # for i in prim.GetChildren():
    #     if i.IsA(UsdRender.Var):
    #         list_mama.append(i.GetPath().pathString)
    find_render_vars(prim, list_mama)
    # print(list_mama)
    crypto_asset = []
    crypto_object = []
    crypto_material = []
    for c in list_mama:
        if 'crypto_asset' in c:
            crypto_asset.append(c)

    for c in list_mama:
        if 'crypto_object' in c:
            crypto_object.append(c)
    for c in list_mama:
        if 'crypto_material' in c:
            crypto_material.append(c)
    list_set = [c for c in list_mama if
                'crypto_asset' not in c and 'crypto_object' not in c and 'crypto_material' not in c]
    # print(list_set)

    if hou.node("..").parm('merage_aov').eval():
        renderproduct = stage.DefinePrim(renderproduct_path + "/renderproduct/renderproduct_all", 'RenderProduct')
        rel = renderproduct.GetRelationship("orderedVars")
        rel.SetTargets(list_mama)

        node_name = hou.node(".").parent().name()
        file_path = f'{path}/aaa/{name}_{node_name}_{version_str}.$F4.{format}'

        attrib_productName = renderproduct.GetAttribute("productName")
        attrib_productName.Set(file_path)
        renderproduct.GetAttribute("productType").Set(ProductType)
        renderproduct.CreateAttribute('arnold:driver', Sdf.ValueTypeNames.String)
        renderproduct.GetAttribute("arnold:driver").Set(f"driver_{format}")

        file_name.set(file_path)
        folder_path = os.path.dirname(file_path)

        # 检查文件夹是否存在
        if not os.path.exists(folder_path):
            # 如果文件夹不存在，则创建文件夹
            os.makedirs(folder_path)




    else:

        file_name.set(f'{path}/<aov>/{name}_<aov>_{version_str}.$F4.{format}')
        # file_name.set(f'{path}/{name}_{version_str}.$F4.{format}')

        renderproduct_list = []
        for list in list_set:

            aov = list.split('/')[-1]

            file_path = (f'{path}/{aov}/{name}_{aov}_{version_str}.$F4.{format}')
            folder_path = os.path.dirname(file_path)

            # 检查文件夹是否存在
            if not os.path.exists(folder_path):
                # 如果文件夹不存在，则创建文件夹
                os.makedirs(folder_path)

            renderproduct = stage.DefinePrim(renderproduct_path + "/renderproduct/renderproduct_" + aov,
                                             'RenderProduct')
            rel = renderproduct.GetRelationship("orderedVars")
            rel.AddTarget(list)

            file_path = f'{path}/{aov}/{name}_{aov}_{version_str}.$F4.{format}'

            if aov == 'rgba':
                file_path = f'{path}/beauty/{name}_beauty_{version_str}.$F4.{format}'

            attrib_productName = renderproduct.GetAttribute("productName")
            attrib_productName.Set(file_path)

            renderproduct.GetAttribute("productType").Set(ProductType)
            renderproduct.CreateAttribute('arnold:driver', Sdf.ValueTypeNames.String)
            renderproduct.GetAttribute("arnold:driver").Set(f"driver_{format}")
            renderproduct_list.append(renderproduct)

        if crypto_asset:
            renderproduct = stage.DefinePrim(renderproduct_path + "/renderproduct/renderproduct_crypto_asset",
                                             'RenderProduct')
            rel = renderproduct.GetRelationship("orderedVars")
            rel.SetTargets(crypto_asset)

            file_path = f'{path}/crypto_asset/{name}_crypto_asset_{version_str}.$F4.{format}'

            attrib_productName = renderproduct.GetAttribute("productName")
            attrib_productName.Set(file_path)
            renderproduct.GetAttribute("productType").Set(ProductType)
            renderproduct.CreateAttribute('arnold:driver', Sdf.ValueTypeNames.String)
            renderproduct.GetAttribute("arnold:driver").Set(f"driver_{format}")
            renderproduct_list.append(renderproduct)
        if crypto_object:
            renderproduct = stage.DefinePrim(renderproduct_path + "/renderproduct/renderproduct_crypto_object",
                                             'RenderProduct')
            rel = renderproduct.GetRelationship("orderedVars")
            rel.SetTargets(crypto_object)

            file_path = f'{path}/crypto_object/{name}_crypto_object_{version_str}.$F4.{format}'

            attrib_productName = renderproduct.GetAttribute("productName")
            attrib_productName.Set(file_path)
            renderproduct.GetAttribute("productType").Set(ProductType)
            renderproduct.CreateAttribute('arnold:driver', Sdf.ValueTypeNames.String)
            renderproduct.GetAttribute("arnold:driver").Set(f"driver_{format}")
            renderproduct_list.append(renderproduct)
        if crypto_material:
            renderproduct = stage.DefinePrim(renderproduct_path + "/renderproduct/renderproduct_crypto_material",
                                             'RenderProduct')
            rel = renderproduct.GetRelationship("orderedVars")
            rel.SetTargets(crypto_material)

            file_path = f'{path}/crypto_material/{name}_crypto_material_{version_str}.$F4.{format}'

            attrib_productName = renderproduct.GetAttribute("productName")
            attrib_productName.Set(file_path)
            renderproduct.GetAttribute("productType").Set(ProductType)
            renderproduct.CreateAttribute('arnold:driver', Sdf.ValueTypeNames.String)
            renderproduct.GetAttribute("arnold:driver").Set(f"driver_{format}")
            renderproduct_list.append(renderproduct)

        for child_prim in renderproduct_list:
            aov = child_prim.GetPath().pathString.split('/')[-1][14:]
            if aov == 'rgba':
                aov = "beauty"
            file_path = (f'{path}/{aov}/{name}_{aov}_{version_str}.$F4.{format}')
            folder_path = os.path.dirname(file_path)
            # print(folder_path)
            if not os.path.exists(folder_path):
                # 如果文件夹不存在，则创建文件夹
                os.makedirs(folder_path)


create_renderproduct()

aov_dict = [
    'diffuse',
    'diffuse_direct',
    'diffuse_indirect',
    'specular',
    'specular_direct',
    'specular_indirect',
    'transmission',
    'transmission_direct',
    'transmission_indirect',
    'sss',
    'sss_direct',
    'sss_indirect',
    'volume',
    'volume_direct',
    'volume_indirect',
    'emission',
    'emission_direct',
    'emission_indirect',
    'coat',
    'albedo',
    'diffuse_albedo',
    'N',
    'P',
    'Z',
    'AO',
    'uv',
    'Use_Cryptomatte',
]

format = hou.parm("../format").menuItems()[hou.parm("../format").eval()]

if format == "deepexr":
    prim_var = stage.DefinePrim(renderproduct_path + '/Vars/rgba', 'RenderVar')
    layer_enable_filtering = prim_var.CreateAttribute('arnold:layer_enable_filtering', Sdf.ValueTypeNames.String)
    layer_enable_filtering.Set('True')
    layer_half_precision = prim_var.CreateAttribute('arnold:layer_half_precision', Sdf.ValueTypeNames.String)
    layer_half_precision.Set('False')
    layer_tolerance = prim_var.CreateAttribute('arnold:layer_tolerance', Sdf.ValueTypeNames.String)
    layer_tolerance.Set('0.25')

    prim = stage.GetPrimAtPath(renderproduct_path + "/renderproduct")

    list_mama = []
    for i in prim.GetChildren():
        list_mama.append(i.GetPath().pathString)
    for list in list_mama:
        renderproduct = stage.DefinePrim(list, 'RenderProduct')
        alpha_tolernace = renderproduct.CreateAttribute('arnold:driver_deepexr:alpha_tolernace',
                                                        Sdf.ValueTypeNames.String)
        alpha_tolernace.Set('0.25')
        depth_tolernace = renderproduct.CreateAttribute('arnold:driver_deepexr:depth_tolernace',
                                                        Sdf.ValueTypeNames.String)
        depth_tolernace.Set('0.25')
        subpixel_merge = renderproduct.CreateAttribute('arnold:driver_deepexr:subpixel_merge',
                                                       Sdf.ValueTypeNames.String)
        subpixel_merge.Set('True')
        attrib_datatype = renderproduct.GetAttribute("productType")
        attrib_datatype.Set("deep")

        attrib_productName = renderproduct.GetAttribute("productName")
        file_name = attrib_productName.Get()
        file_name = file_name.replace('.deepexr', '.exr')
        attrib_productName.Set(file_name)

cam_path = hou.parm('../camera').eval()
overscan = hou.parm('../overscan').eval()
overscan_on = hou.parm('../overscan_enable').eval()
motion = hou.parm('../motion_blur').eval()
if cam_path:
    camera_node = stage.GetPrimAtPath(cam_path)
    if not camera_node.IsValid():
        raise ValueError(f"The camera is missing.")
    cam_prim = stage.GetPrimAtPath(cam_path)
    aperture = cam_prim.GetAttribute("horizontalAperture")
    aperture_attr = aperture.Get()
    if overscan_on:
        aperture = cam_prim.GetAttribute("horizontalAperture")
        aperture_attr = aperture.Get()
        aperture.Set(aperture_attr * overscan)

    if motion:
        shutter_open_attr = cam_prim.GetAttribute("shutter:open")
        shutter_open = hou.parm('../shutter_open').eval()
        shutter_open_attr.Set(shutter_open)

        shutter_close_attr = cam_prim.GetAttribute("shutter:close")
        shutter_close = hou.parm('../shutter_close').eval()
        shutter_close_attr.Set(shutter_close)


def set_metadata():
    hda = hou.node("..")
    parm = hda.parm("custom_metadata")
    instances = parm.multiParmInstances()

    # get your render product primitive
    renderproduct_path = '/Render/Products/renderproduct'
    renderproduct = stage.GetPrimAtPath(renderproduct_path)

    # set compression
    parm_compression = hda.parm("OpenEXR_compression")
    compression_attribute = renderproduct.CreateAttribute("driver:parameters:OpenEXR:compression",
                                                          Sdf.ValueTypeNames.String)
    compression_attribute.Set(parm_compression.eval())

    # loop through multiparm to set metadata to renderproduct
    for i in range(parm.eval()):
        parm_name = hda.parm("metadata_name" + str(i)).eval()
        parm_value = hda.parm("metadata_val" + str(i)).eval()
        try:
            metadata_attribute = renderproduct.CreateAttribute("driver:parameters:OpenEXR:" + parm_name,
                                                               Sdf.ValueTypeNames.String)
            metadata_attribute.Set(parm_value)
        except:
            pass


set_metadata()

# print(list_mama)
is_rendering = hou.contextOption('ropcook')
forceusingdriver = hou.parm("../forceusingdriver").eval()

if forceusingdriver and not is_rendering:
    # renderproduct_path = hou.parm("../renderproduct/primpath").eval()
    if hou.node("..").parm('merage_aov').eval():
        renderproduct_path = '/Render/Products/renderproduct/renderproduct_all'
        renderproduct_prim = stage.GetPrimAtPath(renderproduct_path)

        includeaovs_attr = renderproduct_prim.CreateAttribute("includeAovs", Sdf.ValueTypeNames.Bool)
        includeaovs_attr.Set(True)
    else:
        root_prim = stage.GetPrimAtPath('/Render/Products/renderproduct')
        for child_prim in root_prim.GetChildren():
            # for list in list_mama: #['N','P']:
            #       aov = list.split('/')[-1]
            # renderproduct_path = f'/Render/Products/renderproduct/renderproduct_{aov}'
            # renderproduct_prim = stage.GetPrimAtPath(renderproduct_path)
            # print(renderproduct_prim)

            includeaovs_attr = child_prim.CreateAttribute("includeAovs", Sdf.ValueTypeNames.Bool)
            includeaovs_attr.Set(True)

# renderproduct to rendersetting
ordered_crypto = stage.DefinePrim('/Render/Products/renderproduct')
renderproduct = []
for ordered in ordered_crypto.GetChildren():
    renderproduct.append(str(ordered.GetPath()))

hou.parm("./Ordered_Products").set(" ".join(renderproduct))

