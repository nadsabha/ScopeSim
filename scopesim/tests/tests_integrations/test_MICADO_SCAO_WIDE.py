# One drunken wednesday evening after the consortium dinner, Kieran decided to
# test whether scopesim v1.0 actually works with the MICADO data.
# For this he needs the following test:
# * does the OpticalTrain load with a mvp-micado-yaml file
# * does the OpticalTrain.optics_manager have all the effects needed?
# * is the OpticalTrain.image_plane ~12k x 12k pixels in size.
# * can it be observed with a constant PSF?
# * can it be observed with a FV-PSF?
# * if we set all TCs to 1, and the BG to 0, is flux conserved?
#
# The data that we need for this are
# * Mirror list for the ELT and MICADO
# * atmo, detector, filter TC/QE curves
# * a FV PSF
# * a detector list
# * a spectrum of a bunch of stars and their positions
# * a yaml file which contains the description of MICADO

import os

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.colors import LogNorm

import synphot as sp
from astropy import units as u

import scopesim as sim
from scopesim.commands.user_commands2 import UserCommands
from scopesim.optics.optical_train import OpticalTrain
from scopesim.optics.optics_manager import OpticsManager
from scopesim.optics.fov_manager import FOVManager
from scopesim.optics.image_plane import ImagePlane
from scopesim import effects as efs

TEST_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__),
                            "../mocks/MICADO_SCAO_WIDE/"))
sim.rc.__search_path__ = [TEST_PATH]

PLOTS = True


class Test_MICADO_MVP_YAML:
    def test_yaml_file_can_be_loaded_into_optical_train(self):
        filename = os.path.join(TEST_PATH, "MICADO_SCAO_WIDE_2.config")
        cmds = UserCommands(filename=filename)
        assert isinstance(cmds, UserCommands)
        assert isinstance(cmds.yaml_dicts, list)

        opt = OpticalTrain(cmds=cmds)
        assert isinstance(opt, OpticalTrain)
        assert isinstance(opt.optics_manager, OpticsManager)
        assert isinstance(opt.optics_manager.get_all(efs.FieldVaryingPSF)[0],
                          efs.FieldVaryingPSF)
        assert isinstance(opt.image_plane, ImagePlane)
        assert opt.image_plane.hdu.header["NAXIS1"] >= 4096
        assert isinstance(opt.fov_manager, FOVManager)
        assert len(opt.fov_manager.fovs) == 64

        if not PLOTS:
            for fov in opt.fov_manager.fovs:
                sky_cnrs, det_cnrs = fov.corners
                plt.plot(sky_cnrs[0], sky_cnrs[1])
            plt.show()

        from scopesim.source.source2 import Source

        r = np.arange(-25, 25)
        x, y = np.meshgrid(r, r)
        x = x.flatten() * u.arcsec
        y = y.flatten() * u.arcsec
        ref = [0]*len(x)
        weight = [1]*len(x)
        spec = sp.SourceSpectrum(sp.Empirical1D, points=[0.5, 3.0]*u.um,
                                 lookup_table=[1e3, 1e3]*u.Unit("ph s-1 m-2 um-1"))
        src = Source(x=x, y=y, ref=ref, weight=weight, spectra=[spec])
        opt.observe(src)

        plt.imshow(opt.image_plane.image.T, origin="lower", norm=LogNorm())
        plt.colorbar()
        plt.show()
