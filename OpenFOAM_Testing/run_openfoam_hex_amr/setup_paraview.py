# trace generated using paraview version 6.0.20251023
#import paraview
#paraview.compatibility.major = 6
#paraview.compatibility.minor = 0

#### import the simple module from the paraview
from paraview.simple import *
#### disable automatic camera reset on 'Show'
paraview.simple._DisableFirstRenderCameraReset()

# create a new 'Open FOAM Reader'
run_openfoam_hex_amrfoam = OpenFOAMReader(registrationName='run_openfoam_hex_amr.foam', FileName='/home/cyrillyxj/Projects/Pintle_Optimization/OpenFOAM_Testing/run_openfoam_hex_amr/run_openfoam_hex_amr.foam')

# get animation scene
animationScene1 = GetAnimationScene()

# update animation scene based on data timesteps
animationScene1.UpdateAnimationUsingDataTimeSteps()

# get active view
renderView1 = GetActiveViewOrCreate('RenderView')

# show data in view
run_openfoam_hex_amrfoamDisplay = Show(run_openfoam_hex_amrfoam, renderView1, 'UnstructuredGridRepresentation')

# trace defaults for the display properties.
run_openfoam_hex_amrfoamDisplay.Representation = 'Surface'

# reset view to fit data
renderView1.ResetCamera(False, 0.9)

# get the material library
materialLibrary1 = GetMaterialLibrary()

# update the view to ensure updated data information
renderView1.Update()

# Properties modified on run_openfoam_hex_amrfoam
run_openfoam_hex_amrfoam.CaseType = 'Decomposed Case'

# update animation scene based on data timesteps
animationScene1.UpdateAnimationUsingDataTimeSteps()

animationScene1.GoToLast()

# create a new 'Contour'
contour1 = Contour(registrationName='Contour1', Input=run_openfoam_hex_amrfoam)

# Properties modified on run_openfoam_hex_amrfoam
run_openfoam_hex_amrfoam.Set(
    MeshRegions=['internalMesh', 'lagrangian/dropletCloud'],
    CellArrays=['U', 'alpha.lox', 'cellLevel', 'p', 'p_rgh', 'psi', 'rAU'],
    LagrangianArrays=['U', 'd', 'nParticle', 'origId', 'origProcId', 'y', 'yDot'],
)

# Properties modified on contour1
contour1.Set(
    ContourBy=['POINTS', 'alpha.lox'],
    Isosurfaces=[0.1],
)

# show data in view
contour1Display = Show(contour1, renderView1, 'GeometryRepresentation')

# trace defaults for the display properties.
contour1Display.Representation = 'Surface'

# hide data in view
Hide(run_openfoam_hex_amrfoam, renderView1)

# show color bar/color legend
contour1Display.SetScalarBarVisibility(renderView1, True)

# update the view to ensure updated data information
renderView1.Update()

# get color transfer function/color map for 'alphalox'
alphaloxLUT = GetColorTransferFunction('alphalox')
alphaloxLUT.Set(
    RGBPoints=GenerateRGBPoints(
        range_min=0.10000000149011612,
        range_max=0.10001526027917862,
    ),
    ScalarRangeInitialized=1.0,
)

# get opacity transfer function/opacity map for 'alphalox'
alphaloxPWF = GetOpacityTransferFunction('alphalox')
alphaloxPWF.Set(
    Points=[0.10000000149011612, 0.0, 0.5, 0.0, 0.10001526027917862, 1.0, 0.5, 0.0],
    ScalarRangeInitialized=1,
)

# get 2D transfer function for 'alphalox'
alphaloxTF2D = GetTransferFunction2D('alphalox')

# set scalar coloring
ColorBy(contour1Display, ('CELLS', 'U', 'Magnitude'))

# Hide the scalar bar for this color map if no visible data is colored by it.
HideScalarBarIfNotNeeded(alphaloxLUT, renderView1)

# rescale color and/or opacity maps used to include current data range
contour1Display.RescaleTransferFunctionToDataRange(True, False)

# show color bar/color legend
contour1Display.SetScalarBarVisibility(renderView1, True)

# get color transfer function/color map for 'U'
uLUT = GetColorTransferFunction('U')
uLUT.Set(
    RGBPoints=GenerateRGBPoints(
        range_min=0.0005984858915116136,
        range_max=151.63116001661908,
    ),
    ScalarRangeInitialized=1.0,
)

# get opacity transfer function/opacity map for 'U'
uPWF = GetOpacityTransferFunction('U')
uPWF.Set(
    Points=[0.0005984858915116136, 0.0, 0.5, 0.0, 151.63116001661908, 1.0, 0.5, 0.0],
    ScalarRangeInitialized=1,
)

# get 2D transfer function for 'U'
uTF2D = GetTransferFunction2D('U')

# create a new 'Open FOAM Reader'
run_openfoam_hex_amrfoam_1 = OpenFOAMReader(registrationName='run_openfoam_hex_amr.foam', FileName='/home/cyrillyxj/Projects/Pintle_Optimization/OpenFOAM_Testing/run_openfoam_hex_amr/run_openfoam_hex_amr.foam')

# Properties modified on run_openfoam_hex_amrfoam_1
run_openfoam_hex_amrfoam_1.CaseType = 'Decomposed Case'

# show data in view
run_openfoam_hex_amrfoam_1Display = Show(run_openfoam_hex_amrfoam_1, renderView1, 'GeometryRepresentation')

# trace defaults for the display properties.
run_openfoam_hex_amrfoam_1Display.Representation = 'Surface'

# update the view to ensure updated data information
renderView1.Update()

# set scalar coloring
ColorBy(run_openfoam_hex_amrfoam_1Display, ('FIELD', 'vtkBlockColors'))

# show color bar/color legend
run_openfoam_hex_amrfoam_1Display.SetScalarBarVisibility(renderView1, True)

# get color transfer function/color map for 'vtkBlockColors'
vtkBlockColorsLUT = GetColorTransferFunction('vtkBlockColors')
vtkBlockColorsLUT.Set(
    InterpretValuesAsCategories=1,
    AnnotationsInitialized=1,
    Annotations=['0', '0', '1', '1', '2', '2', '3', '3', '4', '4', '5', '5', '6', '6', '7', '7', '8', '8', '9', '9', '10', '10', '11', '11'],
    ActiveAnnotatedValues=['0', '1'],
    IndexedColors=[1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.63, 0.63, 1.0, 0.67, 0.5, 0.33, 1.0, 0.5, 0.75, 0.53, 0.35, 0.7, 1.0, 0.75, 0.5],
)

# get opacity transfer function/opacity map for 'vtkBlockColors'
vtkBlockColorsPWF = GetOpacityTransferFunction('vtkBlockColors')
vtkBlockColorsPWF.Points = [189473271.125, 0.0, 0.5, 0.0, 308320000.0, 1.0, 0.5, 0.0]

# get 2D transfer function for 'vtkBlockColors'
vtkBlockColorsTF2D = GetTransferFunction2D('vtkBlockColors')

# Properties modified on run_openfoam_hex_amrfoam_1
run_openfoam_hex_amrfoam_1.Set(
    MeshRegions=['lagrangian/dropletCloud'],
    CellArrays=['U', 'alpha.lox', 'cellLevel', 'p', 'p_rgh', 'psi', 'rAU'],
    LagrangianArrays=['U', 'd', 'nParticle', 'origId', 'origProcId', 'y', 'yDot'],
)

# update the view to ensure updated data information
renderView1.Update()

# create a new 'Glyph'
glyph1 = Glyph(registrationName='Glyph1', Input=run_openfoam_hex_amrfoam_1,
    GlyphType='Arrow')

# Properties modified on glyph1
glyph1.Set(
    GlyphType='Sphere',
    OrientationArray=['POINTS', 'No orientation array'],
    ScaleArray=['CELLS', 'd'],
    ScaleFactor=0.1,
    GlyphMode='All Points',
)

# show data in view
glyph1Display = Show(glyph1, renderView1, 'GeometryRepresentation')

# trace defaults for the display properties.
glyph1Display.Representation = 'Surface'

# update the view to ensure updated data information
renderView1.Update()

# hide data in view
Hide(run_openfoam_hex_amrfoam_1, renderView1)

# set active source
SetActiveSource(contour1)

# create a new 'Reflect'
reflect1 = Reflect(registrationName='Reflect1', Input=contour1)

# Properties modified on reflect1
reflect1.Plane = 'Y'

# show data in view
reflect1Display = Show(reflect1, renderView1, 'UnstructuredGridRepresentation')

# hide data in view
Hide(contour1, renderView1)

# show color bar/color legend
reflect1Display.SetScalarBarVisibility(renderView1, True)

# update the view to ensure updated data information
renderView1.Update()

# create a new 'Reflect'
reflect2 = Reflect(registrationName='Reflect2', Input=reflect1)

# Properties modified on reflect2
reflect2.Plane = 'Z'

# show data in view
reflect2Display = Show(reflect2, renderView1, 'UnstructuredGridRepresentation')

# hide data in view
Hide(reflect1, renderView1)

# show color bar/color legend
reflect2Display.SetScalarBarVisibility(renderView1, True)

# update the view to ensure updated data information
renderView1.Update()

# set scalar coloring
ColorBy(reflect2Display, ('CELLS', 'U', 'Magnitude'))

# Hide the scalar bar for this color map if no visible data is colored by it.
HideScalarBarIfNotNeeded(alphaloxLUT, renderView1)

# rescale color and/or opacity maps used to include current data range
reflect2Display.RescaleTransferFunctionToDataRange(True, False)

# show color bar/color legend
reflect2Display.SetScalarBarVisibility(renderView1, True)

# set active source
SetActiveSource(glyph1)

# create a new 'Reflect'
reflect3 = Reflect(registrationName='Reflect3', Input=glyph1)

# Properties modified on reflect3
reflect3.Plane = 'Y'

# show data in view
reflect3Display = Show(reflect3, renderView1, 'UnstructuredGridRepresentation')

# hide data in view
Hide(glyph1, renderView1)

# update the view to ensure updated data information
renderView1.Update()

# create a new 'Reflect'
reflect4 = Reflect(registrationName='Reflect4', Input=reflect3)

# Properties modified on reflect4
reflect4.Plane = 'Z'

# show data in view
reflect4Display = Show(reflect4, renderView1, 'UnstructuredGridRepresentation')

# hide data in view
Hide(reflect3, renderView1)

# update the view to ensure updated data information
renderView1.Update()

# create a new 'Open FOAM Reader'
run_openfoam_hex_amrfoam_2 = OpenFOAMReader(registrationName='run_openfoam_hex_amr.foam', FileName='/home/cyrillyxj/Projects/Pintle_Optimization/OpenFOAM_Testing/run_openfoam_hex_amr/run_openfoam_hex_amr.foam')

# Properties modified on run_openfoam_hex_amrfoam_2
run_openfoam_hex_amrfoam_2.MeshRegions = ['patch/pintleDomain_inlet_f', 'patch/pintleDomain_inlet_o', 'patch/pintleDomain_wall_i', 'patch/pintleDomain_wall_of']

# show data in view
run_openfoam_hex_amrfoam_2Display = Show(run_openfoam_hex_amrfoam_2, renderView1, 'GeometryRepresentation')

# update the view to ensure updated data information
renderView1.Update()

# set scalar coloring
ColorBy(run_openfoam_hex_amrfoam_2Display, ('FIELD', 'vtkBlockColors'))

# show color bar/color legend
run_openfoam_hex_amrfoam_2Display.SetScalarBarVisibility(renderView1, True)

# create a new 'Reflect'
reflect5 = Reflect(registrationName='Reflect5', Input=run_openfoam_hex_amrfoam_2)

# show data in view
reflect5Display = Show(reflect5, renderView1, 'UnstructuredGridRepresentation')

# hide data in view
Hide(run_openfoam_hex_amrfoam_2, renderView1)

# update the view to ensure updated data information
renderView1.Update()

# set scalar coloring
ColorBy(reflect5Display, ('FIELD', 'vtkBlockColors'))

# show color bar/color legend
reflect5Display.SetScalarBarVisibility(renderView1, True)

# Properties modified on reflect5
reflect5.Plane = 'Y'

# update the view to ensure updated data information
renderView1.Update()

# create a new 'Reflect'
reflect6 = Reflect(registrationName='Reflect6', Input=reflect5)

# Properties modified on reflect6
reflect6.Plane = 'Z'

# show data in view
reflect6Display = Show(reflect6, renderView1, 'UnstructuredGridRepresentation')

# hide data in view
Hide(reflect5, renderView1)

# update the view to ensure updated data information
renderView1.Update()

# set scalar coloring
ColorBy(reflect6Display, ('FIELD', 'vtkBlockColors'))

# show color bar/color legend
reflect6Display.SetScalarBarVisibility(renderView1, True)

# turn off scalar coloring
ColorBy(reflect6Display, None)

# Hide the scalar bar for this color map if no visible data is colored by it.
HideScalarBarIfNotNeeded(vtkBlockColorsLUT, renderView1)

# change solid color
reflect6Display.Set(
    AmbientColor=[0.6784313725490196, 0.6784313725490196, 0.6784313725490196],
    DiffuseColor=[0.6784313725490196, 0.6784313725490196, 0.6784313725490196],
)

# create a new 'Open FOAM Reader'
run_openfoam_hex_amrfoam_3 = OpenFOAMReader(registrationName='run_openfoam_hex_amr.foam', FileName='/home/cyrillyxj/Projects/Pintle_Optimization/OpenFOAM_Testing/run_openfoam_hex_amr/run_openfoam_hex_amr.foam')

# Properties modified on run_openfoam_hex_amrfoam_3
run_openfoam_hex_amrfoam_3.Set(
    CaseType='Decomposed Case',
    MeshRegions=['patch/pintleDomain_wall_ch'],
)

# show data in view
run_openfoam_hex_amrfoam_3Display = Show(run_openfoam_hex_amrfoam_3, renderView1, 'GeometryRepresentation')

# update the view to ensure updated data information
renderView1.Update()

# set scalar coloring
ColorBy(run_openfoam_hex_amrfoam_3Display, ('FIELD', 'vtkBlockColors'))

# show color bar/color legend
run_openfoam_hex_amrfoam_3Display.SetScalarBarVisibility(renderView1, True)

# Properties modified on run_openfoam_hex_amrfoam_3
run_openfoam_hex_amrfoam_3.Set(
    MeshRegions=['patch/pintleDomain_wall_ch'],
    CellArrays=['U', 'alpha.lox', 'cellLevel', 'p', 'p_rgh', 'psi', 'rAU'],
    LagrangianArrays=['U', 'd', 'nParticle', 'origId', 'origProcId', 'y', 'yDot'],
)

# update the view to ensure updated data information
renderView1.Update()

# set active source
SetActiveSource(run_openfoam_hex_amrfoam_1)

# set active source
SetActiveSource(run_openfoam_hex_amrfoam_3)

# create a new 'Reflect'
reflect7 = Reflect(registrationName='Reflect7', Input=run_openfoam_hex_amrfoam_3)

# Properties modified on reflect7
reflect7.Plane = 'Z'

# show data in view
reflect7Display = Show(reflect7, renderView1, 'UnstructuredGridRepresentation')

# hide data in view
Hide(run_openfoam_hex_amrfoam_3, renderView1)

# show color bar/color legend
reflect7Display.SetScalarBarVisibility(renderView1, True)

# update the view to ensure updated data information
renderView1.Update()

# get color transfer function/color map for 'p'
pLUT = GetColorTransferFunction('p')
pLUT.Set(
    AutomaticRescaleRangeMode='Rescale to visible data range every timestep',
    RGBPoints=GenerateRGBPoints(
        range_min=-2885.429931640625,
        range_max=164.80799865722656,
    ),
    ScalarRangeInitialized=1.0,
)

# get opacity transfer function/opacity map for 'p'
pPWF = GetOpacityTransferFunction('p')
pPWF.Set(
    Points=[-2885.429931640625, 0.0, 0.5, 0.0, 164.80799865722656, 1.0, 0.5, 0.0],
    ScalarRangeInitialized=1,
)

# get 2D transfer function for 'p'
pTF2D = GetTransferFunction2D('p')

# turn off scalar coloring
ColorBy(reflect7Display, None)

# Hide the scalar bar for this color map if no visible data is colored by it.
HideScalarBarIfNotNeeded(pLUT, renderView1)

# change solid color
reflect7Display.Set(
    AmbientColor=[0.6784313725490196, 0.6784313725490196, 0.6784313725490196],
    DiffuseColor=[0.6784313725490196, 0.6784313725490196, 0.6784313725490196],
)

# hide data in view
Hide(reflect4, renderView1)

# set active source
SetActiveSource(reflect4)

# show data in view
reflect4Display = Show(reflect4, renderView1, 'UnstructuredGridRepresentation')

# hide data in view
Hide(reflect4, renderView1)

# show data in view
reflect4Display = Show(reflect4, renderView1, 'UnstructuredGridRepresentation')

# set active source
SetActiveSource(glyph1)

# set active source
SetActiveSource(run_openfoam_hex_amrfoam_1)

# set active source
SetActiveSource(run_openfoam_hex_amrfoam_1)

# show data in view
run_openfoam_hex_amrfoam_1Display = Show(run_openfoam_hex_amrfoam_1, renderView1, 'GeometryRepresentation')

# show color bar/color legend
run_openfoam_hex_amrfoam_1Display.SetScalarBarVisibility(renderView1, True)

# hide data in view
Hide(run_openfoam_hex_amrfoam_1, renderView1)

# set active source
SetActiveSource(reflect4)

# set active source
SetActiveSource(glyph1)

# set active source
SetActiveSource(reflect4)

# change solid color
reflect4Display.Set(
    AmbientColor=[0.0, 1.0, 0.0],
    DiffuseColor=[0.0, 1.0, 0.0],
)

# set active source
SetActiveSource(glyph1)

# Properties modified on glyph1
glyph1.ScaleFactor = 1.0

# update the view to ensure updated data information
renderView1.Update()

#================================================================
# addendum: following script captures some of the application
# state to faithfully reproduce the visualization during playback
#================================================================

# get layout
layout1 = GetLayout()

#--------------------------------
# saving layout sizes for layouts

# layout/tab size in pixels
layout1.SetSize(1137, 692)

#-----------------------------------
# saving camera placements for views

# current camera placement for renderView1
renderView1.Set(
    CameraPosition=[-0.022850188538136185, -0.03223039115050632, 0.06771191290802815],
    CameraFocalPoint=[0.02705516570804931, -0.018001552192263938, 0.010466676532502238],
    CameraViewUp=[0.7353533154807954, 0.11069564703866278, 0.6685820631291972],
    CameraParallelScale=0.04286725290451818,
)


##--------------------------------------------
## You may need to add some code at the end of this python script depending on your usage, eg:
#
## Render all views to see them appears
# RenderAllViews()
#
## Interact with the view, usefull when running from pvpython
# Interact()
#
## Save a screenshot of the active view
# SaveScreenshot("path/to/screenshot.png")
#
## Save a screenshot of a layout (multiple splitted view)
# SaveScreenshot("path/to/screenshot.png", GetLayout())
#
## Save all "Extractors" from the pipeline browser
# SaveExtracts()
#
## Save a animation of the current active view
# SaveAnimation()
#
## Please refer to the documentation of paraview.simple
## https://www.paraview.org/paraview-docs/nightly/python/
##--------------------------------------------