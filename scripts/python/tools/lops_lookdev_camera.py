# _*_ coding: utf-8 _*_
# .@FileName:lops_lookdev_camera
# .@Date....:2025-05-25 : 10 : 43
# .@Aurhor..:冥羽
# .@Contact.:1942598111@qq.com
'''
launch:
        import lops_lookdev_camera as Qs_FileName
        reload(FileName)
        FileName.main()
'''
import hou
from husd import assetutils
from pxr import Usd, Gf, UsdGeom

def create_lookdev_camera():
    """
    Create a lookdev camera based on a bbox for the asset
    and allows you to load your own camera
    """
    node = hou.pwd()
    stage = node.editableStage()

    # Build the parameters using the ParamTemplateGroup
    _create_parameters(node)

    # Get parameters values
    target_path = node.evalParm("target")
    camera_path = node.evalParm("camera_path")
    spin = node.evalParm("spin")
    pitch = node.evalParm("pitch")
    distance = node.evalParm("distance")
    animate = node.evalParm("animate")
    frames = node.evalParm("frames")
    start_frame = node.evalParm("start_frame")
    use_existing_camera = node.evalParm("use_existing_camera")
    existing_camera_path = node.evalParm("existing_camera_path")

    # Ensure that the target path is valid
    if not target_path.startswith('/'):
        target_path = '/' + target_path

    # Get the target prim
    target_prim = stage.GetPrimAtPath(target_path)
    # Use the BBoxCache instead; directly using extentsInt is annoying/painful
    bbox_cache = UsdGeom.BBoxCache(Usd.TimeCode.EarliestTime(), ['default', 'render'])
    bounds = bbox_cache.ComputeLocalBound(target_prim).GetBox()

    # Check which camera to use
    camera_to_use = existing_camera_path if use_existing_camera else camera_path

    # Check if the camera exists
    existing_camera = None

    if use_existing_camera:
        existing_prim = stage.GetPrimAtPath(existing_camera_path)
        if existing_prim and existing_prim.IsA(UsdGeom.Camera):
            existing_camera = UsdGeom.Camera(existing_prim)
            print(existing_camera)
        else:
            raise hou.NodeError(f"Existing camera not found at: {existing_camera_path}")

    # Create or use the camera
    if existing_camera:
        camera = existing_camera
    else:
        camera = UsdGeom.Camera.Define(stage, camera_path)
        # Asset settings to the new camera
        camera.GetHorizontalApertureAttr().Set(36.0)
        camera.GetVerticalApertureAttr().Set(24.0)
        camera.GetFocalLengthAttr().Set(50.0)
        camera.GetClippingRangeAttr().Set(Gf.Vec2f(0.01, 100000.0))

    if animate:
        for frame in range(frames):
            # Create an animated camera by setting the matrix values at each frame
            current_frame = start_frame + frame
            time_code = Usd.TimeCode(current_frame)

            # Calculate the spin angle based on the frame
            current_spin = spin + (frame / frames * 360.0)

            # Create a temporary stage to generate the camera transforms
            temp_stage = Usd.Stage.CreateInMemory()
            temp_camera = _create_framed_camera(temp_stage, bounds, pitch, current_spin, distance)

            # Get the transform matrix
            temp_xform = UsdGeom.Xformable(temp_camera)

            for xform_op in temp_xform.GetOrderedXformOps():
                if xform_op.GetOpName().endswith("frameToBounds"):
                    matrix = xform_op.Get()

                    # Apply the matrix to our actual camera at this time sample
                    main_xform_camera = UsdGeom.Xformable(camera)
                    if frame == 0:
                        transform_op = main_xform_camera.AddTransformOp(opSuffix="orbitTransform")
                        transform_op.Set(matrix)
                    else:
                        # Get the existing transform op
                        for op in main_xform_camera.GetOrderedXformOps():
                            if op.GetOpName().endswith("orbitTransform"):
                                # Set the matrix at this time sample
                                op.Set(matrix, time_code)
                                break
                    break


    else:
        # Static camera setup
        # Create cameras using the method createFramedCameraToBounds

        if existing_camera:
            # For existing camera, add a transform to place the camera
            main_xform_camera = UsdGeom.Xformable(camera)

            # Create a temporary stage to generate the camera transforms
            temp_stage = Usd.Stage.CreateInMemory()
            temp_camera = _create_framed_camera(temp_stage, bounds, pitch, spin, distance)

            # Get the transform matrix
            temp_xform = UsdGeom.Xformable(temp_camera)

            for xform_op in temp_xform.GetOrderedXformOps():
                if xform_op.GetOpName().endswith("frameToBounds"):
                    matrix = xform_op.Get()

                    transform_op = main_xform_camera.AddTransformOp(opSuffix="orbitTransform")
                    transform_op.Set(matrix)
                    break

        else:
            # Create a new camera
            assetutils.createFramedCameraToBounds(
                stage,
                bounds,
                cameraprimpath=camera_path,
                rotatex=25 + pitch,
                rotatey=35 + spin,
                offsetdistance=distance
            )


def _create_framed_camera(stage, bounds, pitch, spin, distance):
    '''
    Creates a Thumbnail Camera using the assetutils' createFramedCameraToBounds method
    Args:
        bounds, primpath, pitch, spin, distance
    Return:
        temp_camera = The camera generated by the createFramedCameraToBounds method
    '''

    # Create a temporary stage to generate the camera transforms
    temp_camera = assetutils.createFramedCameraToBounds(
        stage,
        bounds,
        cameraprimpath = "/TempCamera",
        rotatex=25+pitch,
        rotatey=35+spin,
        offsetdistance=distance
    )
    return temp_camera


def _create_parameters(node):
    """Function to create the parameters needed for the LookDev Camera"""

    ptg = node.parmTemplateGroup()


    find_parm = ptg.find("target")

    if not find_parm:
        new_folder = hou.FolderParmTemplate(
            name="camera_folder",
            label="Lookdev Camera Settings",
        )

        target_string = hou.StringParmTemplate(
            name="target",
            label="Target Prim",
            num_components=1
        )

        camera_string = hou.StringParmTemplate(
            name="camera_path",
            label="Camera Path",
            num_components=1,
            default_value=("/ThumbnailCamera"),
        )

        spin_float = hou.FloatParmTemplate(
            name="spin",
            label="Spin Camera",
            num_components=1,
            default_value=(0,),
            min=-180.0,
            max=180.0
        )

        pitch_float = hou.FloatParmTemplate(
            name="pitch",
            label="Pitch Camera",
            num_components=1,
            default_value=(0,),
            min=-90.0,
            max=90.0
        )

        distance_float = hou.FloatParmTemplate(
            name="distance",
            label="Distance",
            num_components=1,
            default_value=(0,),
            min=0.0,
            max=20.0
        )

        animated_cam_folder = hou.FolderParmTemplate(
            name="animated_folder",
            label="LookDev Animated Camera Settings",
        )

        animate_toggle = hou.ToggleParmTemplate(
            name="animate",
            label="Animate",
        )

        use_camera = hou.ToggleParmTemplate(
            name="use_existing_camera",
            label="Use Existing Camera",
            disable_when="{animate == 0}"
        )

        camera_path = hou.StringParmTemplate(
            name="existing_camera_path",
            label="Existing Camera Path",
            num_components=1,
            disable_when="{ use_existing_camera == 0 }"
        )

        num_frames = hou.IntParmTemplate(
            name="frames",
            label="Number of Frames",
            num_components=1,
            default_value=(60,),
            min=30,
            disable_when="{ animate == 0 }"
        )

        start_frame = hou.IntParmTemplate(
            name="start_frame",
            label="Start Frame",
            num_components=1,
            default_value=(0,),
            disable_when="{ animate == 0 }"
        )

        new_folder.addParmTemplate(target_string)
        new_folder.addParmTemplate(camera_string)
        new_folder.addParmTemplate(spin_float)
        new_folder.addParmTemplate(pitch_float)
        new_folder.addParmTemplate(distance_float)
        ptg.append(new_folder)
        animated_cam_folder.addParmTemplate(animate_toggle)
        animated_cam_folder.addParmTemplate(use_camera)
        animated_cam_folder.addParmTemplate(camera_path)
        animated_cam_folder.addParmTemplate(num_frames)
        animated_cam_folder.addParmTemplate(start_frame)
        ptg.append(animated_cam_folder)

        node.setParmTemplateGroup(ptg)