import os
import unittest
from __main__ import vtk, qt, ctk, slicer
import EditorLib
from EditorLib import EditorLib
from EditorLib.EditOptions import HelpButton
from EditorLib.EditOptions import EditOptions
from EditorLib import EditUtil
from EditorLib import LabelEffect
#
# DrawSplineEffect
#

class DrawSplineEffect:
  def __init__(self, parent):
    parent.title = "Draw Spline Effect" 
    parent.categories = ["Developer Tools.Editor Extensions"]
    parent.dependencies = []
    parent.contributors = ["Ricardo A Corredor (EPFL / LTS5)"] # replace with "Firstname Lastname (Organization)"
    parent.helpText = """
    Tool for drawing splines.
    """
    parent.acknowledgementText = """
    This file was originally developed by Ricardo A. Corredor, EPFL / LTS5 thanks to Slicer and SlicerRT community support.
    """ 

    # Add this extension to the editor's list for discovery when the module
    # is created. Since this module may be discovered before the Editor itself,
    # create the list if it doesn't already exist.
    try:
      slicer.modules.editorExtensions
    except AttributeError:
      slicer.modules.editorExtensions = {}
    slicer.modules.editorExtensions['DrawSplineEffect'] = DrawSplineEffectExtension

#
# DrawSplineEffectWidget
#

class DrawSplineEffectWidget:
  
  def __init__(self, parent = None):
    self.parent = parent

  def setup(self):
    pass

  def cleanup(self):
    pass

#########################################################
#
#
comment = """

  DrawSplineEffect is a subclass of DrawSplineEffect
  that implements the interactive spline tool
  in the slicer editor

# TODO :
"""
#
#########################################################

#
# DrawSplineEffectOptions - see DrawSplineEffect, EditOptions and Effect for superclasses
#

class DrawSplineEffectOptions(LabelEffect.LabelEffectOptions):
  """ DrawSplineEffect-specfic gui
  """

  def __init__(self, parent=0):
    super(DrawSplineEffectOptions,self).__init__(parent)

  def __del__(self):
    super(DrawSplineEffectOptions,self).__del__()

  def create(self):
    super(DrawSplineEffectOptions,self).create()

    self.apply = qt.QPushButton("Apply", self.frame)
    self.apply.objectName = self.__class__.__name__ + 'Apply'
    self.apply.setToolTip("Apply current outline.\nUse the 'a' or 'Enter' hotkey to apply in slice window")
    self.frame.layout().addWidget(self.apply)
    self.widgets.append(self.apply)

    EditorLib.HelpButton(self.frame, "Use this tool to draw an outline.\n\nLeft Click: add point.\nLeft Drag: add multiple points.\nx: delete last point.\na: apply outline.")

    self.connections.append( (self.apply, 'clicked()', self.onApply) )

    # Add vertical spacer
    self.frame.layout().addStretch(1)

  def onApply(self):
    for tool in self.tools:
      tool.apply()

  def destroy(self):
    super(DrawSplineEffectOptions,self).destroy()

  # note: this method needs to be implemented exactly as-is
  # in each leaf subclass so that "self" in the observer
  # is of the correct type
  def updateParameterNode(self, caller, event):
    node = self.editUtil.getParameterNode()
    if node != self.parameterNode:
      if self.parameterNode:
        node.RemoveObserver(self.parameterNodeTag)
      self.parameterNode = node
      self.parameterNodeTag = node.AddObserver(vtk.vtkCommand.ModifiedEvent, self.updateGUIFromMRML)

  def setMRMLDefaults(self):
    super(DrawSplineEffectOptions,self).setMRMLDefaults()

  def updateGUIFromMRML(self,caller,event):
    super(DrawSplineEffectOptions,self).updateGUIFromMRML(caller,event)

  def updateMRMLFromGUI(self):
    disableState = self.parameterNode.GetDisableModifiedEvent()
    self.parameterNode.SetDisableModifiedEvent(1)
    super(DrawSplineEffectOptions,self).updateMRMLFromGUI()
    self.parameterNode.SetDisableModifiedEvent(disableState)
    if not disableState:
      self.parameterNode.InvokePendingModifiedEvent()

#
# DrawSplineEffectTool
#

class DrawSplineEffectTool(LabelEffect.LabelEffectTool):
  """
  One instance of this will be created per-view when the effect
  is selected.  It is responsible for implementing feedback and
  label map changes in response to user input.
  This class observes the editor parameter node to configure itself
  and queries the current view for background and label volume
  nodes to operate on.
  """

  def __init__(self, sliceWidget):

    # keep a flag since events such as sliceNode modified
    # may come during superclass construction, which will
    # invoke our processEvents method
    self.initialized = False

    super(DrawSplineEffectTool,self).__init__(sliceWidget)

    # create a logic instance to do the non-gui work
    self.logic = DrawSplineEffectLogic(self.sliceWidget.sliceLogic())

    # interaction state variables
    self.activeSlice = None
    self.lastInsertSLiceNodeMTime = None
    self.actionState = None

    # initialization
    self.xyPoints = vtk.vtkPoints()
    self.rasPoints = vtk.vtkPoints()
    self.polyData = self.createPolyData()

    # ---- RaC SOS
    self.controlPoints = vtk.vtkPoints()
    # One spline for each direction.
    self.aSplineX = vtk.vtkKochanekSpline()
    self.aSplineY = vtk.vtkKochanekSpline()
    self.aSplineZ = vtk.vtkKochanekSpline()
    # ---- RaC EOS

    self.mapper = vtk.vtkPolyDataMapper2D()
    self.actor = vtk.vtkActor2D()
    if vtk.VTK_MAJOR_VERSION <= 5:
      self.mapper.SetInput(self.polyData)
    else:
      self.mapper.SetInputData(self.polyData)
    self.actor.SetMapper(self.mapper)
    property_ = self.actor.GetProperty()
    property_.SetColor(1,1,0)
    property_.SetLineWidth(1)
    self.renderer.AddActor2D( self.actor )
    self.actors.append( self.actor )

    self.initialized = True

  def cleanup(self):
    """
    call superclass to clean up actor
    """
    super(DrawSplineEffectTool,self).cleanup()

  def setLineMode(self,mode="solid"):
    property_ = self.actor.GetProperty()
    if mode == "solid":
      property_.SetLineStipplePattern(65535)
    elif mode == "dashed":
      property_.SetLineStipplePattern(0xff00)

  def processEvent(self, caller=None, event=None):
    """
    handle events from the render window interactor
    """

    if super(DrawSplineEffectTool,self).processEvent(caller,event):
      return

    if not self.initialized:
      return

    # events from the interactor
    if event == "LeftButtonPressEvent":
      if self.actionState != "editing":
        self.actionState = "drawing"
        self.cursorOff()
        xy = self.interactor.GetEventPosition()
        self.addPoint(self.logic.xyToRAS(xy))
        self.abortEvent(event)
    elif event == "LeftButtonReleaseEvent":
      if self.actionState != "editing":
        self.actionState = "drawing"
        self.cursorOn()
    elif event == "RightButtonPressEvent":
      sliceNode = self.sliceWidget.sliceLogic().GetSliceNode()
      self.lastInsertSLiceNodeMTime = sliceNode.GetMTime()
      xy = self.interactor.GetEventPosition()
      self.addPoint(self.logic.xyToRAS(xy))
      self.aSplineX.ClosedOn()
      self.aSplineY.ClosedOn()
      self.aSplineZ.ClosedOn()
      self.repaint()
    elif event == "RightButtonReleaseEvent":
      sliceNode = self.sliceWidget.sliceLogic().GetSliceNode()
      if self.lastInsertSLiceNodeMTime == sliceNode.GetMTime():
        #self.apply()
        self.actionState = "editing"
    elif event == "MouseMoveEvent":
      if self.actionState == "drawing":
        xy = self.interactor.GetEventPosition()
        self.repaint()
        #self.addPoint(self.logic.xyToRAS(xy))
        #self.abortEvent(event)
    elif event == "KeyPressEvent":
      key = self.interactor.GetKeySym()
      if key == 'a' or key == 'Return':
        self.apply()
        self.abortEvent(event)
    else:
      pass

    # events from the slice node
    if caller and caller.IsA('vtkMRMLSliceNode'):
      #
      # make sure all points are on the current slice plane
      # - if the SliceToRAS has been modified, then we're on a different plane
      #
      sliceLogic = self.sliceWidget.sliceLogic()
      lineMode = "solid"
      currentSlice = sliceLogic.GetSliceOffset()
      if self.activeSlice:
        offset = abs(currentSlice - self.activeSlice)
        if offset > 0.01:
          lineMode = "dashed"
      self.setLineMode(lineMode)

    self.positionActors()

  def positionActors(self):
    """
    update draw feedback to follow slice node
    """
    sliceLogic = self.sliceWidget.sliceLogic()
    sliceNode = sliceLogic.GetSliceNode()
    rasToXY = vtk.vtkTransform()
    rasToXY.SetMatrix( sliceNode.GetXYToRAS() )
    rasToXY.Inverse()
    self.xyPoints.Reset()
    rasToXY.TransformPoints( self.rasPoints, self.xyPoints )
    self.polyData.Modified()
    self.sliceView.scheduleRender()

  def apply(self):

    lines = self.polyData.GetLines()
    if lines.GetNumberOfCells() == 0: return

    # close the polyline back to the first point
    idArray = lines.GetData()
    p = idArray.GetTuple1(1)
    idArray.InsertNextTuple1(p)
    idArray.SetTuple1(0, idArray.GetNumberOfTuples() - 1)

    self.logic.undoRedo = self.undoRedo
    self.logic.applyPolyMask(self.polyData)
    self.resetPolyData()
    self.controlPoints.Reset()
    self.aSplineX.RemoveAllPoints()
    self.aSplineY.RemoveAllPoints()
    self.aSplineZ.RemoveAllPoints()
    self.logic.resetFiducials()

  def createPolyData(self):
    """make an empty single-polyline polydata"""

    polyData = vtk.vtkPolyData()
    polyData.SetPoints(self.xyPoints)

    lines = vtk.vtkCellArray()
    polyData.SetLines(lines)
    idArray = lines.GetData()
    idArray.Reset()
    idArray.InsertNextTuple1(0)

    polygons = vtk.vtkCellArray()
    polyData.SetPolys(polygons)
    idArray = polygons.GetData()
    idArray.Reset()
    idArray.InsertNextTuple1(0)

    return polyData


  def resetPolyData(self):
    """return the polyline to initial state with no points"""
    lines = self.polyData.GetLines()
    idArray = lines.GetData()
    idArray.Reset()
    idArray.InsertNextTuple1(0)
    self.xyPoints.Reset()
    self.rasPoints.Reset()
    lines.SetNumberOfCells(0)
    self.activeSlice = None

  def addPoint(self,ras):
    """add a world space point to the current outline"""
    # store active slice when first point is added
    sliceLogic = self.sliceWidget.sliceLogic()
    currentSlice = sliceLogic.GetSliceOffset()
    if not self.activeSlice:
      self.activeSlice = currentSlice
      self.setLineMode("solid")
    
    # don't allow adding points on except on the active slice (where
    # first point was laid down)
    if self.activeSlice != currentSlice: return
    
    # keep track of node state (in case of pan/zoom)
    sliceNode = sliceLogic.GetSliceNode()
    self.lastInsertSliceNodeMTime = sliceNode.GetMTime()
    
    
    # Total number of points.
    numberOfInputPoints = self.controlPoints.GetNumberOfPoints()
    self.controlPoints.InsertPoint(numberOfInputPoints, ras[0], ras[1], ras[2])
    self.aSplineX.AddPoint(numberOfInputPoints, ras[0])
    self.aSplineY.AddPoint(numberOfInputPoints, ras[1])
    self.aSplineZ.AddPoint(numberOfInputPoints, ras[2])
    self.logic.addFiducial(ras)
    numberOfInputPoints = numberOfInputPoints + 1
    

    # if numberOfInputPoints > 1:
      
    #   # Number of points on the spline
    #   numberOfOutputPoints = 100
    #   # Interpolate x, y and z by using the three spline filters and
    #   # create new points
      
    #   self.resetPolyData()
    #   lines = self.polyData.GetLines()
    #   idArray = lines.GetData()
    #   for i in range(0, numberOfOutputPoints):
    #     t = (numberOfInputPoints-1.0)/(numberOfOutputPoints-1.0)*i
    #     self.rasPoints.InsertPoint(i,self.aSplineX.Evaluate(t), self.aSplineY.Evaluate(t),self.aSplineZ.Evaluate(t))
    #     idArray.InsertNextTuple1(i)
    #   idArray.SetTuple1(0, idArray.GetNumberOfTuples()-1)
    #   lines.SetNumberOfCells(1)

    

  def deleteLastPoint(self):
    """unwind through addPoint list back to empy polydata"""

    pcount = self.rasPoints.GetNumberOfPoints()
    if pcount <= 0: return

    pcount = pcount - 1
    self.rasPoints.SetNumberOfPoints(pcount)

    lines = self.polyData.GetLines()
    idArray = lines.GetData()
    idArray.SetTuple1(0, pcount)
    idArray.SetNumberOfTuples(pcount+1)

    self.positionActors()

  def repaint(self):
    numberOfInputPoints = self.controlPoints.GetNumberOfPoints()
    if numberOfInputPoints > 0:
      
      # Number of points on the spline
      numberOfOutputPoints = 200
      # Interpolate x, y and z by using the three spline filters and
      # create new points
      if self.actionState == "drawing":
        xy = self.interactor.GetEventPosition()
        ras = self.logic.xyToRAS(xy)
        if self.controlPoints.GetNumberOfPoints() == self.aSplineX.GetNumberOfPoints():
          self.aSplineX.AddPoint(numberOfInputPoints, ras[0])
          self.aSplineY.AddPoint(numberOfInputPoints, ras[1])
          self.aSplineZ.AddPoint(numberOfInputPoints, ras[2])
          numberOfInputPoints+=1
        else:
          numberOfInputPoints = self.aSplineX.GetNumberOfPoints()
          self.aSplineX.RemovePoint(numberOfInputPoints-1)
          self.aSplineY.RemovePoint(numberOfInputPoints-1)
          self.aSplineZ.RemovePoint(numberOfInputPoints-1)
          self.aSplineX.AddPoint(numberOfInputPoints-1, ras[0])
          self.aSplineY.AddPoint(numberOfInputPoints-1, ras[1])
          self.aSplineZ.AddPoint(numberOfInputPoints-1, ras[2])
      
      lines = self.polyData.GetLines()
      idArray = lines.GetData()
      idArray.Reset()
      idArray.InsertNextTuple1(0)
      self.xyPoints.Reset()
      self.rasPoints.Reset()
      lines.SetNumberOfCells(0)
      for i in range(0, numberOfOutputPoints):
        t = (numberOfInputPoints-1.0)/(numberOfOutputPoints-1.0)*i
        self.rasPoints.InsertPoint(i,self.aSplineX.Evaluate(t), self.aSplineY.Evaluate(t),self.aSplineZ.Evaluate(t))
        idArray.InsertNextTuple1(i)
      idArray.SetTuple1(0, idArray.GetNumberOfTuples()-1)
      lines.SetNumberOfCells(1)

#
# DrawSplineEffectLogic
#

class DrawSplineEffectLogic(LabelEffect.LabelEffectLogic):
  """
  This class contains helper methods for a given effect
  type.  It can be instanced as needed by an DrawSplineEffectTool
  or DrawSplineEffectOptions instance in order to compute intermediate
  results (say, for user feedback) or to implement the final
  segmentation editing operation.  This class is split
  from the DrawSplineEffectTool so that the operations can be used
  by other code without the need for a view context.
  """

  def __init__(self,sliceLogic):
    super(DrawSplineEffectLogic,self).__init__(sliceLogic)
    self.fiducials = None
    self.isNewContour = True
    self.numberFiducials = 0
    self.observerTags = [] # for monitoring fiducial changes
    

  def addFiducial(self,ras):
    if self.isNewContour == True:
      self.fiducials = slicer.vtkMRMLMarkupsFiducialNode()
      self.fiducials.SetScene( slicer.mrmlScene )
      slicer.mrmlScene.AddNode( self.fiducials )
      tag = self.fiducials.AddObserver(self.fiducials.PointModifiedEvent, lambda caller,event: self.onFiducialMoved(caller))
      print tag
      self.observerTags.append( (self.fiducials,tag) )
      self.isNewContour = False
    
    self.numberFiducials += 1    
    self.fiducials.AddFiducial(ras[0],ras[1],ras[2],str(self.numberFiducials))

  def resetFiducials(self):
    self.isNewContour=True

  def onFiducialMoved(self,fiducialList):
    """Callback when fiducialList's point has been changed.
    Check the Markups.State attribute to see if it is being
    actively moved and if so, skip the picked method."""
    self.movingView = fiducialList.GetAttribute('Markups.MovingInSliceView')
    movingIndexAttribute = fiducialList.GetAttribute('Markups.MovingMarkupIndex')
    if self.movingView and movingIndexAttribute:
      movingIndex = int(movingIndexAttribute)
      pos = [0,0,0]
      fiducialList.GetNthFiducialPosition(movingIndex,pos)
      print pos


#
# The DrawSplineEffect class definition
#

class DrawSplineEffectExtension(LabelEffect.LabelEffect):
  """Organizes the Options, Tool, and Logic classes into a single instance
  that can be managed by the EditBox
  """

  def __init__(self):
    # name is used to define the name of the icon image resource (e.g. DrawSplineEffect.png)
    self.name = "DrawSplineEffect"
    # tool tip is displayed on mouse hover
    self.toolTip = "Draw: draw outlines - apply with right click or 'a' key"

    self.options = DrawSplineEffectOptions
    self.tool = DrawSplineEffectTool
    self.logic = DrawSplineEffectLogic
