"""
State:          place_light_highlight
State type:     Place_light_Highlight
Description:    Place Light Highlight
Author:         Administrator
Date Created:   May 22, 2025 - 22:17:28
"""

import hou
import viewerstate.utils as su


class State(object):
    def __init__(self, state_name, scene_viewer):
        self.state_name = state_name
        self.scene_viewer = scene_viewer
        self.obj = hou.node('/obj')

        # Settings for the light
        self.light = None
        self.light_distance = 1

    def onEnter(self, kwargs):
        """ Called on node bound states when it starts
        """

        state_parms = kwargs["state_parms"]

    def onExit(self, kwargs):
        """ Called when the state terminates
        """
        state_parms = kwargs["state_parms"]

    def onInterrupt(self, kwargs):
        """ Called when the state is interrupted e.g when the mouse
        moves outside the viewport
        """
        pass

    def onResume(self, kwargs):
        """ Called when an interrupted state resumes
        """
        pass

    def onMouseEvent(self, kwargs):
        """ Process mouse and tablet events
        """
        ui_event = kwargs["ui_event"]
        dev = ui_event.device()

        # Must return True to consume the event
        return False

    def onMouseWheelEvent(self, kwargs):
        """ Process a mouse wheel event
        """

        ui_event = kwargs["ui_event"]
        state_parms = kwargs["state_parms"]

        # Must return True to consume the event
        return False

    def onMenuAction(self, kwargs):
        """ Callback implementing the actions of a bound menu. Called
        when a menu item has been selected.
        """

        menu_item = kwargs["menu_item"]
        state_parms = kwargs["state_parms"]

    def onKeyEvent(self, kwargs):
        """ Called for processing a keyboard event
        """
        ui_event = kwargs["ui_event"]
        state_parms = kwargs["state_parms"]

        # Must returns True to consume the event
        return False

    def onDraw(self, kwargs):
        """ Called for rendering a state e.g. required for
        hou.AdvancedDrawable objects
        """
        draw_handle = kwargs["draw_handle"]

    def onSelection(self, kwargs):
        """ Called when a selector has selected something
        """
        selection = kwargs["selection"]
        state_parms = kwargs["state_parms"]
        selector_name = "light_select"

        if len(selection) != 1:
            return False

        if selector_name == "light_select":
            self.light = selection[0]
            hou.ui.displayMessage(f"{self.light.name()} is selected", severity=hou.severityType.Message)
            return True

    def onGenerate(self, kwargs):
        """ Called when a nodeless state starts
        """
        state_parms = kwargs["state_parms"]


def createViewerStateTemplate():
    """ Mandatory entry point to create and return the viewer state
        template to register. """

    state_typename = "_place_light"
    state_label = "place_light_highlight"
    state_cat = hou.objNodeTypeCategory()

    template = hou.ViewerStateTemplate(state_typename, state_label, state_cat)
    template.bindFactory(State)
    template.bindIcon("MTSC_python")

    template.bindObjectSelector(
        prompt="Select a light",
        quick_select=True,
        auto_start=True,
        use_existing_selection=True,
        allow_multisel=False,
        secure_selection=hou.secureSelectionOption.Ignore,
        allowed_types=('hlight::2.0',),
        name='light_select'
    )

    return template
