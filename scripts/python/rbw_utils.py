import hou
import os

def reload_package(kwargs):
    """
    This is a function that reloads the my_tools package and
    the python modules inside the my_tools package.
    Args:
         kwargs: Going to check if the Alt key is pressed.
         If it is, it will reload the python modules.
    """
    import hou
    import importlib
    import os
    import sys
    # reload the package
    package_path = hou.text.expandString("$HOUDINI_USER_PREF_DIR/packages/") + 'my_tools.json'

    hou.ui.reloadPackage(package_path)

    # reload the python modules
    folder_path = hou.text.expandString('$RBW/scripts/python')

    for root, dirs, files in os.walk(folder_path):
        sys.path.append(root)
        for file in files:
            if file.endswith('.py') and file != "__init__.py":
                module_path = os.path.join(root, file).replace(os.sep, '/')
                module_name = os.path.relpath(module_path, folder_path).replace(os.sep, ".").replace('.py', '')


                try:
                    if module_name in sys.modules:
                        if kwargs["altclick"] == True:
                            importlib.reload(sys.modules[module_name])
                            print(f"Reloaded module:{module_name}")
                    else:
                        importlib.import_module(module_name)
                        print(f"{module_name} was imported")
                except Exception as error:
                    print(f'Failed to import or reload the module {module_name}:{error}')

            
    # reload the menus

    hou.hscript("menurefresh")
    # reload the shelves

    #shelves = hou.shelves.shelves()
    path_shelves = hou.text.expandString("$RBW/toolbar")

    for root, dir, files in os.walk(path_shelves):
        for file in files:
            if file.endswith(".shelf"):
                shelf_path = os.path.join(root, file).replace(os.sep, "/")
                hou.shelves.loadFile(shelf_path)

# def testfunction(kwargs):
#     if kwargs["altclick"] == True:
#         print("alt click")
#     else:
#         print("not alt click")

def check_path_valid(path):
    """
    This is a function that checks if a path is valid.
    Args:
        path: The path to be checked.
    Returns:
        True if the path is valid, False otherwise.
    """
    import hou
    import os

    # Fix the path if is using a Env.
    path = os.path.dirname(hou.text.expandString(path))

    # Check if the path exists and is a directory and we have access to it.

    if os.path.exists(path) and os.access(path, os.R_OK):
        print(f"The path {path} is valid.")
        return True
    else:
        print(f"The path {path} is not valid.")
        hou.ui.displayMessage(f"{path} is not valid.Please try again.", title="Error")