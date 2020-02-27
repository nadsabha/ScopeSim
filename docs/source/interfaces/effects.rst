Effect object interface
=======================

Custom ``Effect`` objects are made by subclassing the ``Effect`` object.
The following three methods need to be included in any subclassed effect:

- ``.__init__()`` : Loads (non-lazy) relevant data from file, if necessary,
- ``.fov_grid()`` : provides information for the initial construction of the
  list of FOV objects
- ``.apply_to()`` : accepts an object, alters it somehow, returns the object


``.__init__(**kwargs)``
-----------------------


``.fov_grid(which=<str>, **kwargs)``
------------------------------------
which : str
    ["waveset", "edges", "shifts"] where:
    * waveset - wavelength bin extremes
    * edges - on sky coordinate edges for each FOV box
    * shifts - wavelength dependent FOV position offsets


``.apply_to(obj)``
------------------
where ``obj`` can be an instance of one of the following:

- ``Source``,
- ``FieldOfView``,
- ``ImagePlane``,
- ``Detector``


See Also
--------
Effect, Source, FieldOfView, ImagePlane, Detector