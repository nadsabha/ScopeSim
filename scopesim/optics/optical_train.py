from copy import deepcopy

from .. import rc
from ..commands.user_commands import UserCommands
from .optics_manager import OpticsManager
from .fov_manager import FOVManager
from .image_plane import ImagePlane
from ..detector import DetectorArray
from ..utils import from_currsys


class OpticalTrain:
    """
    The main class for controlling a simulation

    Parameters
    ----------
    cmds : UserCommands, str
        If the name of an instrument is passed, OpticalTrain tries to find the
        instrument package, and internally creates the UserCommands object

    Examples
    --------
    Create an optical train::

        >>> import scopesim as im
        >>> cmd = sim.UserCommands("MICADO")
        >>> opt = sim.OpticalTrain(cmd)

    Observe a Source object::

        >>> src = sim.source.source_templates.empty_sky()
        >>> opt.observe(src)
        >>> hdus = opt.readout()

    List the effects modelled in an OpticalTrain::

        >>> print(opt.effects)

    Effects can be accessed by using the name of the effect::

        >>> print(opt["dark_current"])

    To include or exclude an effect during a simulation run, use the
    ``.include`` attribute of the effect::

         >>> opt["dark_current"].include = False

    Data used by an Effect object is contained in the ``.data`` attribute, while
    other information is contained in the ``.meta`` attribute::

        >>> opt["dark_current"].data
        >>> opt["dark_current"].meta

    Meta data values can be set by either using the ``.meta`` attribute
    directly::

        >>> opt["dark_current"].meta["value"] = 0.5

    or by passing a dictionary (with one or multiple entries) to the
    OpticalTrain object::

        >>> opt["dark_current"] = {"value": 0.75, "dit": 30}

    """

    def __init__(self, cmds=None):

        self.cmds = cmds
        self.optics_manager = None
        self.fov_manager = None
        self.image_planes = []
        self.detector_arrays = []
        self.yaml_dicts = None

        if cmds is not None:
            self.load(cmds)

    def load(self, user_commands):
        """
        (Re)Loads an OpticalTrain with a new set of UserCommands

        Parameters
        ----------
        user_commands : UserCommands

        """

        if isinstance(user_commands, str):
            user_commands = UserCommands(use_instrument=user_commands)

        if not isinstance(user_commands, UserCommands):
            raise ValueError("user_commands must be a UserCommands object: "
                             "{}".format(type(user_commands)))

        self.cmds = user_commands
        rc.__currsys__ = user_commands
        self.yaml_dicts = rc.__currsys__.yaml_dicts
        self.optics_manager = OpticsManager(self.yaml_dicts)
        self.update()

    def update(self, **kwargs):
        """
        Update the user-defined parameters and remake the main internal classes

        Parameters
        ----------
        kwargs : **dict
            Any keyword-value pairs from a config file

        """
        self.optics_manager.update(**kwargs)
        opt_man = self.optics_manager

        self.fov_manager = FOVManager(opt_man.fov_setup_effects, **kwargs)
        self.image_planes = [ImagePlane(hdr, **kwargs)
                             for hdr in opt_man.image_plane_headers]
        self.detector_arrays = [DetectorArray(det_list, **kwargs)
                                for det_list in opt_man.detector_setup_effects]

    def observe(self, orig_source, update=False, **kwargs):
        """
        Main controlling method for observing ``Source`` objects

        Parameters
        ----------
        orig_source : Source
        update : bool
            Reload optical system
        kwargs : **dict
            Any keyword-value pairs from a config file

        Notes
        -----
        How the list of Effects is split between the 5 main tasks:

        .. todo:: List is out of date - update
        - Make a FOV list - z_order = 0..99
        - Make a image plane - z_order = 100..199
        - Apply Source altering effects - z_order = 200..299
        - Apply FOV specific (3D) effects - z_order = 300..399
        - Apply FOV-independent (2D) effects - z_order = 400..499
        - [Apply detector plane (0D, 2D) effects - z_order = 500..599]

        """
        if update:
            self.update(**kwargs)

        self.set_focus(kwargs)    # put focus back on current instrument package

        source = deepcopy(orig_source)

        # [1D - transmission curves]
        for effect in self.optics_manager.source_effects:
            source = effect.apply_to(source)

        # [3D - Atmospheric shifts, PSF, NCPAs, Grating shift/distortion]
        fovs = self.fov_manager.fovs
        for fov_i, fov in enumerate(fovs):
            # print("FOV", fov_i+1, "of", n_fovs, flush=True)
            fov.extract_from(source)
            fov.view()

            for effect in self.optics_manager.fov_effects:
                fov = effect.apply_to(fov)

            self.image_planes[fov.image_plane_id].add(fov.hdu, wcs_suffix="D")
            # ..todo: finish off the multiple image plane stuff

        # [2D - Vibration, flat fielding, chopping+nodding]
        for effect in self.optics_manager.image_plane_effects:
            for ii in range(len(self.image_planes)):
                self.image_planes[ii] = effect.apply_to(self.image_planes[ii])

    def readout(self, filename=None, **kwargs):
        """

        Parameters
        ----------
        filename : str
        kwargs

        Returns
        -------
        hdu : fits.HDUList

        Notes
        -----
        - Apply detector plane (0D, 2D) effects - z_order = 500..599

        """

        hdus = []
        for detector_array in self.detector_arrays:
            dtcr_effects = self.optics_manager.detector_effects
            hdu = detector_array.readout(self.image_planes, dtcr_effects,
                                         **kwargs)

            if filename is not None and isinstance(filename, str):
                hdu.writeto(filename, overwrite=True)

            hdus += [hdu]

        return hdus

    def set_focus(self, kwargs):
        self.cmds.update(**kwargs)
        dy = self.cmds.default_yamls
        if len(dy) > 0 and "packages" in dy:
            self.cmds.update(packages=self.default_yamls[0]["packages"])
        rc.__currsys__ = self.cmds

    @property
    def effects(self):
        return self.optics_manager.list_effects()

    def __getitem__(self, item):
        return self.optics_manager[item]

    def __setitem__(self, key, value):
        self.optics_manager[key] = value

