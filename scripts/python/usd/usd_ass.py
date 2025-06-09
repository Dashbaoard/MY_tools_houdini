# _*_ coding: utf-8 _*_
# .@FileName:usd_ass
# .@Date....:2025-06-08 : 22 : 32
# .@Aurhor..:冥羽
# .@Contact.:1942598111@qq.com
'''
launch:
        import usd_ass as Qs_FileName
        reload(FileName)
        FileName.main()
'''
# _*_ coding: utf-8 _*_
# .@FileName:create_rubbertoy_usd
# .@Date....:2025-06-08 : 17 : 07
# .@Aurhor..:冥羽
# .@Contact.:1942598111@qq.com

from pxr import Usd, UsdGeom, Sdf, Kind


def create_rubbertoy_file(file_path, payload_path=None):
    """
    创建类似rubbertoy.usda的结构

    参数:
        file_path: 输出的USD文件路径
        payload_path: 引用的payload文件路径(可选)
    """
    try:
        # 创建新stage
        stage = Usd.Stage.CreateNew(file_path)

        # 设置全局元数据
        stage.SetMetadata("metersPerUnit", 1)
        stage.SetMetadata("upAxis", "Y")
        stage.SetMetadata("timeCodesPerSecond", 24)
        stage.SetMetadata("framesPerSecond", 24)

        # 创建class层级
        class_prim = stage.CreateClassPrim("/__class__")
        rubbertoy_class = stage.CreateClassPrim("/__class__/rubbertoy")

        # 创建主Xform
        rubbertoy = stage.DefinePrim("/rubbertoy", "Xform")
        stage.SetDefaultPrim(rubbertoy)

        # 添加GeomModelAPI
        geom_model_api = UsdGeom.ModelAPI.Apply(rubbertoy)
        # geom_model_api.SetKind(Kind.Tokens.component)

        # 设置assetInfo
        asset_info = {
            "identifier": Sdf.AssetPath("./rubbertoy.usd"),
            "name": "rubbertoy",
            "thumbnail": Sdf.AssetPath("./thumbnail.png")
        }
        rubbertoy.SetAssetInfo(asset_info)

        # 设置继承关系
        inherits = rubbertoy.GetInherits()
        inherits.AddInherit("/__class__/rubbertoy")

        # 设置extentsHint
        extents = [(-1.012149, -0.26760602, -0.972831), (1.012149, 1.3846359, 0.847423)]
        UsdGeom.ModelAPI(rubbertoy).SetExtentsHint(extents)

        # 添加payload（如果提供了路径）
        if payload_path:
            rubbertoy.GetPayloads().AddPayload(Sdf.Payload(payload_path))

        # 保存文件
        stage.GetRootLayer().Save()
        print(f"成功创建rubbertoy文件: {file_path}")
        return True

    except Exception as e:
        print(f"创建文件失败: {str(e)}")
        return False


# 使用示例
if __name__ == "__main__":
    output_file = r"E:/usd/export/v001/assert01.usda"
    payload_file = r"E:/usd/export/v001/payload01.usda"  # 可以是None如果不需payload

    create_rubbertoy_file(output_file, payload_file)