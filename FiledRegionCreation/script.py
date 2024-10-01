# -*- coding: utf-8 -*-
__title__   = "Filled Regions"
__doc__     = """Version = 2.0
Date    = 30.09.2024
________________________________________________________________
Description:

Use this to quickly visualize room boundaries or create filled Regions for plans and diagrams.
This version shows only rooms visible in the current view, for both current and linked models.

________________________________________________________________
TODO:
1. Open the desired floor plan view in Revit.
2. Click this button to run the script.
3. Select a model (current or linked).
4. Select visible rooms from the list that appears.
5. Select a filled region type.
6. The script will create filled regions for selected rooms visible in the current view.
________________________________________________________________
Last Updates:
- [30.09.2024] v2.0 Updated room visibility check for both current and linked models
________________________________________________________________
Author: Durai"""

from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import *
from pyrevit import revit, DB, UI
from pyrevit import script
from pyrevit import forms

import clr
clr.AddReference('System')
from System.Collections.Generic import List

app = __revit__.Application
uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

def create_filled_region_for_room(room, view, filled_region_type, transform=None):
    boundary_options = SpatialElementBoundaryOptions()
    boundary_segments = room.GetBoundarySegments(boundary_options)
    
    if not boundary_segments:
        return False
    
    curve_loop = CurveLoop()
    for segment in boundary_segments[0]:
        curve = segment.GetCurve()
        if transform:
            curve = curve.CreateTransformed(transform)
        curve_loop.Append(curve)
    
    try:
        FilledRegion.Create(doc, filled_region_type.Id, view.Id, List[CurveLoop]([curve_loop]))
        return True
    except:
        return False

def get_filled_region_types():
    return FilteredElementCollector(doc).OfClass(FilledRegionType).ToElements()

def get_linked_models():
    return FilteredElementCollector(doc).OfClass(RevitLinkInstance).ToElements()

def is_room_visible_in_view(room, view, transform=None):
    bbox = room.get_BoundingBox(None)
    if bbox is None:
        return False
    
    if transform:
        bbox_min = transform.OfPoint(bbox.Min)
        bbox_max = transform.OfPoint(bbox.Max)
    else:
        bbox_min = bbox.Min
        bbox_max = bbox.Max
    
    view_bbox = view.get_BoundingBox(None)
    return (bbox_max.X > view_bbox.Min.X and bbox_min.X < view_bbox.Max.X and
            bbox_max.Y > view_bbox.Min.Y and bbox_min.Y < view_bbox.Max.Y and
            bbox_max.Z > view_bbox.Min.Z and bbox_min.Z < view_bbox.Max.Z)

def get_visible_rooms_in_view(view, model):
    if isinstance(model, Document):
        rooms = FilteredElementCollector(model) \
            .OfCategory(BuiltInCategory.OST_Rooms) \
            .WhereElementIsNotElementType() \
            .ToElements()
        return [room for room in rooms if is_room_visible_in_view(room, view)]
    elif isinstance(model, RevitLinkInstance):
        link_doc = model.GetLinkDocument()
        if link_doc:
            rooms = FilteredElementCollector(link_doc) \
                .OfCategory(BuiltInCategory.OST_Rooms) \
                .WhereElementIsNotElementType() \
                .ToElements()
            
            transform = model.GetTotalTransform()
            return [room for room in rooms if is_room_visible_in_view(room, view, transform)]
    else:
        return []
    
    
def main():
    active_view = doc.ActiveView
    if not isinstance(active_view, ViewPlan):
        forms.alert("Please run this script in a plan view.", title="Invalid View")
        return

    linked_models = get_linked_models()
    model_options = ["Current Model"] + [link.Name for link in linked_models]
    
    selected_model = forms.SelectFromList.show(
        model_options,
        title='Select Model',
        multiselect=False
    )
    
    if not selected_model:
        return

    if selected_model == "Current Model":
        rooms = get_visible_rooms_in_view(active_view, doc)
        transform = None
    else:
        link_instance = next((link for link in linked_models if link.Name == selected_model), None)
        if not link_instance:
            forms.alert("Selected linked model not found.", title="Error")
            return
        rooms = get_visible_rooms_in_view(active_view, link_instance)
        transform = link_instance.GetTotalTransform()

    if not rooms:
        forms.alert("No visible rooms found in the active view.", title="No Visible Rooms")
        return

    room_options = ["{0}: {1}".format(room.Number, room.get_Parameter(BuiltInParameter.ROOM_NAME).AsString()) for room in rooms]
    selected_rooms = forms.SelectFromList.show(
        room_options,
        title='Select Visible Rooms',
        multiselect=True
    )
    
    if not selected_rooms:
        return

    selected_room_objects = [room for room in rooms if "{0}: {1}".format(room.Number, room.get_Parameter(BuiltInParameter.ROOM_NAME).AsString()) in selected_rooms]

    filled_region_types = list(get_filled_region_types())
    if not filled_region_types:
        forms.alert("No filled region types found in the project.", title="No Filled Region Types")
        return

    filled_region_type_names = [type.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM).AsString() for type in filled_region_types]
    selected_type_name = forms.SelectFromList.show(
        filled_region_type_names,
        title='Select Filled Region Type',
        multiselect=False
    )
    if not selected_type_name:
        return

    selected_type = next((type for type in filled_region_types if type.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM).AsString() == selected_type_name), None)

    if not selected_type:
        forms.alert("Selected type not found.", title="Error")
        return

    success_count = 0
    with revit.Transaction("Create Filled Regions for Visible Rooms"):
        for room in selected_room_objects:
            if create_filled_region_for_room(room, active_view, selected_type, transform):
                success_count += 1

    forms.alert("Filled regions created successfully for {0} out of {1} selected rooms!".format(success_count, len(selected_room_objects)), title="Success")

if __name__ == '__main__':
    main()