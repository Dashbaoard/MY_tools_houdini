# _*_ coding: utf-8 _*_
# .@FileName:usd_payload
# .@Date....:2025-06-08 : 21 : 38
# .@Aurhor..:冥羽
# .@Contact.:1942598111@qq.com
'''
launch:
        import usd_payload as Qs_FileName
        reload(FileName)
        FileName.main()
'''
# _*_ coding: utf-8 _*_
# .@FileName:create_payload
# .@Date....:2025-06-08 : 17 : 07
# .@Aurhor..:冥羽
# .@Contact.:1942598111@qq.com
'''
功能：创建引用geo.usd和mtl.usd的payload文件
用法：
    import create_payload
    create_payload.create_payload_file(
        "E:/usd/payload.usd", 
        "E:/usd/geo.usd", 
        "E:/usd/mtl.usd"
    )
'''
from pxr import Usd, UsdGeom, Sdf


def create_payload_file(payload_path, geo_path, mtl_path):
    """
    创建包含geo和mtl引用的payload文件

    参数:
        payload_path: 要创建的payload文件路径
        geo_path: 几何体USD文件路径
        mtl_path: 材质USD文件路径
    """
    try:
        # 创建新stage
        stage = Usd.Stage.CreateNew(payload_path)

        # 设置根Prim
        root_prim = stage.DefinePrim("/Root")
        stage.SetDefaultPrim(root_prim)

        # 创建几何体引用 (payload方式)
        geo_prim = stage.OverridePrim("/Root")
        geo_prim.GetPayloads().AddPayload(Sdf.Payload(geo_path, "/Root"))

        # 创建材质引用 (payload方式)
        mtl_prim = stage.OverridePrim("/Root")
        mtl_prim.GetPayloads().AddPayload(Sdf.Payload(mtl_path, "/Root"))

        # 保存文件
        stage.GetRootLayer().Save()
        print(f"成功创建payload文件: {payload_path}")
        return True

    except Exception as e:
        print(f"创建payload文件失败: {str(e)}")
        return False


# 使用示例
if __name__ == "__main__":
    # 替换为实际路径
    payload_file = r"E:/usd/export/v001/payload01.usda"
    geo_file = r"E:/usd/export/v001/mod22.usda"
    mtl_file = r"E:/usd/export/v001/mtl26.usda"

    create_payload_file(payload_file, geo_file, mtl_file)