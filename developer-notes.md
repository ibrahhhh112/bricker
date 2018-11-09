* Add Features
    * Add mode for selecting verts at locations next to bricks and adding bricks there
    * SNOT (studs not on top) functionality
    * Add 'exclusion' functionality so that one model doesn’t create bricks where another model already did
    * Generate model with bricks and slopes to more closely approximate original mesh (USER REQUESTED)
    * Add 'select bricks' button in Brick Models dropdown arrow
    * Add customization for custom object offset, size, and brick scale (amount of bricksDict locations it takes up), default to scale/offset for 1x1 brick with stud
    * Add many more brick types, including inverted slopes
    * Improve brick topology for 3D printing
    * Use shader-based bevel as opposed to geometry-based bevel
* Improve Performance
    * For animation, if last frame's brickFreqMatrix matches current frame's brickFreqMatrix, save time by just keeping that model around for another frame or duplicating it for the next frame or something

finish inverted slope before releasing next version
Custom objects shrink if something has changed.
