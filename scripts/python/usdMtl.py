# _*_ coding: utf-8 _*_
# .@FileName:usdMtl
# .@Date....:2025-06-07 : 22 : 26
# .@Aurhor..:冥羽
# .@Contact.:1942598111@qq.com
'''
launch:
        import usdMtl as Qs_FileName
        reload(FileName)
        FileName.main()
'''
arnold_standard_surface = {
    # 基础属性
    "base": {"type": "float", "range": (0.0, 1.0), "desc": "基础权重"},
    "baseColor": {"type": "color3", "default": (0.8, 0.8, 0.8), "desc": "基础颜色"},
    "diffuseRoughness": {"type": "float", "range": (0.0, 1.0), "desc": "漫反射粗糙度"},

    # 高光属性
    "specular": {"type": "float", "range": (0.0, 1.0), "desc": "高光强度"},
    "specularColor": {"type": "color3", "default": (1.0, 1.0, 1.0), "desc": "高光颜色"},
    "specularRoughness": {"type": "float", "range": (0.0, 1.0), "desc": "高光粗糙度"},
    "specularAnisotropy": {"type": "float", "range": (-1.0, 1.0), "desc": "各向异性"},
    "specularRotation": {"type": "float", "range": (0.0, 1.0), "desc": "各向异性旋转"},

    # 金属属性
    "metalness": {"type": "float", "range": (0.0, 1.0), "desc": "金属度"},

    # 透射属性
    "transmission": {"type": "float", "range": (0.0, 1.0), "desc": "透射强度"},
    "transmissionColor": {"type": "color3", "default": (1.0, 1.0, 1.0), "desc": "透射颜色"},
    "transmissionDepth": {"type": "float", "default": 0.5, "desc": "透射深度"},

    # 次表面散射
    "subsurface": {"type": "float", "range": (0.0, 1.0), "desc": "SSS强度"},
    "subsurfaceColor": {"type": "color3", "default": (0.8, 0.8, 0.8), "desc": "SSS颜色"},
    "subsurfaceRadius": {"type": "vector3", "default": (1.0, 1.0, 1.0), "desc": "SSS半径"},

    # 涂层属性
    "coat": {"type": "float", "range": (0.0, 1.0), "desc": "涂层强度"},
    "coatColor": {"type": "color3", "default": (1.0, 1.0, 1.0), "desc": "涂层颜色"},
    "coatRoughness": {"type": "float", "range": (0.0, 1.0), "desc": "涂层粗糙度"},

    # 发射属性
    "emission": {"type": "float", "range": (0.0, 1.0), "desc": "发射强度"},
    "emissionColor": {"type": "color3", "default": (1.0, 1.0, 1.0), "desc": "发射颜色"},

    # 几何体属性
    "opacity": {"type": "float", "range": (0.0, 1.0), "desc": "不透明度"},
    "normalCamera": {"type": "vector3", "desc": "法线贴图输入"}
}



materialx_standard_surface = {
    # 基础属性
    "base": {"type": "float", "range": (0.0, 1.0), "desc": "基础混合权重"},
    "base_color": {"type": "color3", "default": (0.8, 0.8, 0.8), "desc": "基础颜色"},
    "diffuse_roughness": {"type": "float", "range": (0.0, 1.0), "desc": "漫反射粗糙度"},

    # 高光属性
    "specular": {"type": "float", "range": (0.0, 1.0), "desc": "高光强度"},
    "specular_color": {"type": "color3", "default": (1.0, 1.0, 1.0), "desc": "高光颜色"},
    "specular_roughness": {"type": "float", "range": (0.0, 1.0), "desc": "高光粗糙度"},
    "specular_IOR": {"type": "float", "default": 1.5, "desc": "折射率"},
    "specular_anisotropy": {"type": "float", "range": (0.0, 1.0), "desc": "各向异性"},
    "specular_rotation": {"type": "float", "range": (0.0, 1.0), "desc": "各向异性旋转"},

    # 金属属性
    "metalness": {"type": "float", "range": (0.0, 1.0), "desc": "金属度"},

    # 透射属性
    "transmission": {"type": "float", "range": (0.0, 1.0), "desc": "透射强度"},
    "transmission_color": {"type": "color3", "default": (1.0, 1.0, 1.0), "desc": "透射颜色"},
    "transmission_depth": {"type": "float", "default": 0.5, "desc": "透射深度"},

    # 次表面散射
    "subsurface": {"type": "float", "range": (0.0, 1.0), "desc": "SSS强度"},
    "subsurface_color": {"type": "color3", "default": (0.8, 0.8, 0.8), "desc": "SSS颜色"},
    "subsurface_radius": {"type": "vector3", "default": (1.0, 1.0, 1.0), "desc": "SSS半径"},
    "subsurface_scale": {"type": "float", "default": 1.0, "desc": "SSS缩放"},

    # 涂层属性
    "coat": {"type": "float", "range": (0.0, 1.0), "desc": "涂层强度"},
    "coat_color": {"type": "color3", "default": (1.0, 1.0, 1.0), "desc": "涂层颜色"},
    "coat_roughness": {"type": "float", "range": (0.0, 1.0), "desc": "涂层粗糙度"},

    # 发射属性
    "emission": {"type": "color3", "default": (0.0, 0.0, 0.0), "desc": "发射颜色"},
    "emission_weight": {"type": "float", "range": (0.0, 1.0), "desc": "发射强度"},

    # 几何体属性
    "opacity": {"type": "float", "range": (0.0, 1.0), "desc": "不透明度"},
    "normal": {"type": "vector3", "desc": "法线贴图输入"},

    # MaterialX 特有
    "thin_film_thickness": {"type": "float", "range": (0.0, 1000.0), "desc": "薄膜厚度"},
    "thin_film_IOR": {"type": "float", "default": 1.5, "desc": "薄膜折射率"}
}