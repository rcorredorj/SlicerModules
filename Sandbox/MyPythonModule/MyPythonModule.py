import os
import unittest
from __main__ import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *

#
# MyPythonModule
#

class MyPythonModule(ScriptedLoadableModule):
  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "MyPythonModule" # TODO make this more human readable by adding spaces
    self.parent.categories = ["Examples"]
    self.parent.dependencies = []
    self.parent.contributors = ["John Doe (AnyWare Corp.)"] # replace with "Firstname Lastname (Organization)"
    self.parent.helpText = """
    This is an example of scripted loadable module bundled in an extension.
    """
    self.parent.acknowledgementText = """
    This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc.
    and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
""" # replace with organization, grant and thanks.

#
# MyPythonModuleWidget
#

class MyPythonModuleWidget(ScriptedLoadableModuleWidget):

  def __init__(self, parent=None):
    self.parent = parent
    self.logic = None
    self.items=[]

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)
    # Instantiate and connect widgets ...

    #
    # Parameters Area
    #
    parametersCollapsibleButton = ctk.ctkCollapsibleButton()
    parametersCollapsibleButton.text = "Parameters"
    self.layout.addWidget(parametersCollapsibleButton)

    # Layout within the dummy collapsible button
    parametersCollapsibleLayout = qt.QVBoxLayout(parametersCollapsibleButton)

    self.table = qt.QTableWidget()
    self.table.setRowCount(1)
    self.table.setColumnCount(3)
    parametersCollapsibleLayout.addWidget(self.table)
    item = qt.QTableWidgetItem('Test');
    self.table.setItem(0,0,item);
    self.items.append(item)


    #
    # input volume selector
    #
    
    # Add vertical spacer
    self.layout.addStretch(1)

  def cleanup(self):
    pass


#
# MyPythonModuleLogic
#

class MyPythonModuleLogic(ScriptedLoadableModuleLogic):

  def hasImageData(self,volumeNode):
    return True

  def run(self,inputVolume,outputVolume,enableScreenshots=0,screenshotScaleFactor=1):
    return True


class MyPythonModuleTest(ScriptedLoadableModuleTest):

  def setUp(self):
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    self.setUp()

