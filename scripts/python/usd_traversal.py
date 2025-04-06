# import hou
# from numpy.lib.polynomial import roots
#
#
# class UsdTraversal:
#     def __init__(self):
#         self.root = None
#
#     def test(self):
#         print("This is working!")
#
#     def setNewPath(self, root):
#         self.root = root
#         visited = set()
#         old_name = 'lights'
#         new_name = 'new_scene'
#         self._bfs_change_path(root, visited, old_name, new_name)
#
#     def _bfs_change_path(self, root, visited, old_name, new_name):
#         queue = [root]
#         while len(queue) > 0:
#             current = queue.pop(0)
#             if current is visited:
#                 pass
#             else:
#                 self._set_parms(current, old_name, new_name)
#             visited.add(current)
#             for node in current.inputs():
#                 queue.append(node)
#     def _set_parms(self, node, old_name, new_name):
#         for parm in node.parms():
#             if 'path' in parm.name() and parm.name() != "destpath":
#                 old_path = parm.evalAsString()
#
#                 if old_name in old_path:
#                     new_path = old_path.replace(old_name, new_name)
#                     parm.set(new_path)
import hou


import hou
from PySide2 import QtCore, QtWidgets

class UsdTraversal:
    def __init__(self):
        self.root = None

    def test(self):
        print("This is working!")

    def setNewPath(self, root):
        self.root = root
        old_name, new_name = self._get_input_names()
        if old_name and new_name:  # 确保两个名称都已输入
            visited = set()
            self._bfs_change_path(root, visited, old_name, new_name)

    def _get_input_names(self):
        # 创建一个对话框
        dialog = QtWidgets.QDialog()
        dialog.setWindowTitle("Input Names")
        layout = QtWidgets.QFormLayout(dialog)

        # 创建两个输入字段
        self.old_name_edit = QtWidgets.QLineEdit()
        self.new_name_edit = QtWidgets.QLineEdit()

        # 添加输入字段到布局
        layout.addRow("Old Name:", self.old_name_edit)
        layout.addRow("New Name:", self.new_name_edit)

        # 创建并添加确认按钮
        button = QtWidgets.QPushButton("OK")
        button.clicked.connect(dialog.accept)
        layout.addRow(button)

        # 显示对话框并等待用户响应
        dialog.exec_()

        # 获取输入值
        old_name = self.old_name_edit.text()
        new_name = self.new_name_edit.text()

        return old_name, new_name

    def _bfs_change_path(self, root, visited, old_name, new_name):
        queue = [root]
        while queue:
            current = queue.pop(0)
            if current not in visited:
                self._set_parms(current, old_name, new_name)
            visited.add(current)
            for node in current.inputs():
                queue.append(node)

    def _set_parms(self, node, old_name, new_name):
        for parm in node.parms():
            if 'path' in parm.name() and parm.name() != "destpath":
                old_path = parm.evalAsString()
                if old_name in old_path:
                    new_path = old_path.replace(old_name, new_name)
                    parm.set(new_path)