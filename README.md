# README

Bricker is an addon for Blender designed to streamline and, in many cases, automate the modeling, animation, and simulation workflow for LEGO bricks (Blender version: 2.79)

## Bricker
  * Features:
      * Convert any 3D Mesh into a photo-real 3D brick model
      * Generate animated brick models from keyframed animation, simulations (soft and rigid body physics, fluid, smoke and fire, cloth, etc), armature, and much more
      * Customize model resolution, detail, brick type, and more at any time using the simple and intuitive UI.
      * Adjust the auto-generated model using handy tools like split/merge bricks, add adjacent bricks, change brick type, and more!
      * Render your model using the fully integrated ABS Plastic Materials add-on (available separately on the Blender Market) for photorealistic results.
      * Export your LDraw model to any LDR program (e.g. LeoCad, LDD, etc.) for step-by-step building instructions.
  * Instructions:
      * Create a new model with the 'New Model' button, and name it whatever you'd like
      * Select a source object with the 'Source Object' eyedropper (defaults to active object when creating new model)
      * Click 'Brickify Object'
      * Adjust model settings for your desired result
      * Click 'Update Model' to view setting adjustments
      * Once you're satisfied with the settings, make adjustments to your model in the 'Customize Model' dropdown menu
  * Future improvements (developer's notes):
      * Add Features
          * Add mode for selecting verts at locations next to bricks and adding bricks there
          * SNOT (studs not on top) functionality
          * Add 'exclusion' functionality so that one model doesn’t create bricks where another model already did
          * Generate model with bricks and slopes to more closely approximate original mesh (USER REQUESTED)
          * Add 'select bricks' button in Brick Models dropdown arrow
          * Add customization for custom object offset, size, and brick scale (amount of bricksDict locations it takes up), default to scale/offset for 1x1 brick with stud
      * Improve Performance
          * For animation, if last frame's brickFreqMatrix matches current frame's brickFreqMatrix, save time by just keeping that model around for another frame or duplicating it for the next frame or something
      * Other Improvements
          * Alternate merge directions per level for greedy merge type (USER REQUESTED)
          * Add many more brick types, including inverted slopes
          * Transfer matObj functionality to new custom list property
      * Known issues:
          * For models with thin outer shells, Bricker may use color of inside face instead of outside face for brick material (see snapchat hotdog file)
          * Applying model rotation when deleting brickified model whose source has rotated parent produces problematic results
          * In 'Realistic Creek 4' file, Bricker doesn't know which images to use, and simply uses the active UV Map instead of intelligently selecting the UV map affecting that face_idx.
