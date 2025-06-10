# _*_ coding: utf-8 _*_
# .@FileName:usd_geo2
# .@Date....:2025-06-10 : 23 : 26
# .@Aurhor..:冥羽
# .@Contact.:1942598111@qq.com
'''
launch:
        import usd_geo2 as Qs_FileName
        reload(FileName)
        FileName.main()
'''
import maya.cmds as cmds

# 检查是否有选中物体
if not cmds.ls(selection=True):
    cmds.warning("请先选中要导出的物体！")
else:
    # 设置导出选项
    export_path = r"E:\usd\export\v002\mod13.usda"  # 替换为你的路径
    cmds.mayaUSDExport(
        file=export_path,
        sl=True,      # 仅导出选中物体
        #mcp=False,  # 不导出材质
        exportUVs=True,     # 导出UV（可选）
        defaultUSDFormat="usdc",  # 格式：usd, usda, usdc
        shadingMode="none"  # 不导出 shading 数据
    )
    print(f"成功导出: {export_path}")