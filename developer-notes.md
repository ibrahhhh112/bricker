* Add Features
    * SNOT (studs not on top) functionality
    * Add 'exclusion' functionality so that one model doesn’t create bricks where another model already did
    * Generate model with bricks and slopes to more closely approximate original mesh (USER REQUESTED)
    * Add customization for custom object offset, size, and brick scale (amount of bricksDict locations it takes up), default to scale/offset for 1x1 brick with stud
    * Add many more brick types
    * Improve brick topology for 3D printing
    * Use shader-based bevel as opposed to geometry-based bevel

Add advanced option for brickifying in background, and limit min of max_workers to 1.
This should run brickify model in background as well, not just anim
