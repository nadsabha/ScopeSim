import os
from copy import deepcopy
import pytest
from pytest import approx

import numpy as np
from astropy import units as u

import scopesim as sim
from scopesim.optics.fov_manager import FOVManager
from scopesim.optics import fov_manager as fov_mgr
from scopesim.optics.image_plane import ImagePlane
from scopesim.optics.optical_train import OpticalTrain
from scopesim.optics.optics_manager import OpticsManager
from scopesim.utils import find_file
from scopesim.commands.user_commands2 import UserCommands
from scopesim.optics.effects.ter_curves import TERCurve

from scopesim.tests.mocks.py_objects.effects_objects import _mvs_effects_list
from scopesim.tests.mocks.py_objects.yaml_objects import \
    _usr_cmds_min_viable_scope
from scopesim.tests.mocks.py_objects.source_objects import _image_source, \
    _table_source

import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

PLOTS = True

FILES_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                          "../mocks/files/"))
YAMLS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                          "../mocks/yamls/"))

sim.rc.__search_path__ += [FILES_PATH, YAMLS_PATH]


def _basic_cmds():
    return UserCommands(filename=find_file("CMD_mvs_cmds.config"))


@pytest.fixture(scope="function")
def cmds():
    return _basic_cmds()


@pytest.fixture(scope="function")
def tbl_src():
    return _table_source()


@pytest.fixture(scope="function")
def im_src():
    return _image_source()


@pytest.mark.usefixtures("cmds")
class TestInit:
    def test_initialises_with_nothing(self):
        assert isinstance(OpticalTrain(), OpticalTrain)

    def test_initialises_with_basic_commands(self, cmds):
        opt = OpticalTrain(cmds=cmds)
        assert isinstance(opt, OpticalTrain)

    def test_has_observation_dict_object_after_initialising(self, cmds):
        opt = OpticalTrain(cmds=cmds)
        assert len(opt.observation_dict) != 0

    def test_has_optics_manager_object_after_initialising(self, cmds):
        opt = OpticalTrain(cmds=cmds)
        assert isinstance(opt.optics_manager, OpticsManager)

    def test_has_fov_manager_object_after_initialising(self, cmds):
        opt = OpticalTrain(cmds=cmds)
        print(opt.fov_manager)
        assert isinstance(opt.fov_manager, FOVManager)

    def test_has_image_plane_object_after_initialising(self, cmds):
        opt = OpticalTrain(cmds=cmds)
        assert isinstance(opt.image_plane, ImagePlane)

    def test_has_yaml_dict_object_after_initialising(self, cmds):
        opt = OpticalTrain(cmds=cmds)
        assert len(opt.yaml_dicts) == 4


@pytest.mark.usefixtures("cmds", "im_src", "tbl_src")
class TestObserve:
    def test_observe_works_for_table(self, cmds, tbl_src):
        opt = OpticalTrain(cmds)
        opt.observe(tbl_src)

        if PLOTS:
            plt.imshow(opt.image_plane.image.T, origin="lower", norm=LogNorm())
            plt.show()

    def test_observe_works_for_image(self, cmds, im_src):
        opt = OpticalTrain(cmds)
        opt.observe(im_src)

        if PLOTS:
            plt.imshow(opt.image_plane.image.T, origin="lower", norm=LogNorm())
            plt.show()

    def test_observe_works_for_source_distributed_over_several_fovs(self, cmds,
                                                                    im_src):
        orig_sum = np.sum(im_src.fields[0].data)

        cmds["SIM_PIXEL_SCALE"] = 0.02
        opt = OpticalTrain(cmds)
        opt.observe(im_src)

        wave = np.arange(0.5, 2.51, 0.1)*u.um
        unit = u.Unit("ph s-1 m-2 um-1")
        print(opt.optics_manager.surfaces_table.emission(wave).to(unit))
        print(opt.optics_manager.surfaces_table.table)
        final_sum = np.sum(opt.image_plane.image)
        print(orig_sum, final_sum)

        if PLOTS:
            plt.imshow(opt.image_plane.image.T, origin="lower", norm=LogNorm())
            plt.show()

        assert final_sum == approx(orig_sum, rel=1e-3)

    def test_observe_works_for_many_sources_distributed(self, cmds, im_src):
        orig_sum = np.sum(im_src.fields[0].data)
        im_src1 = deepcopy(im_src)
        im_src2 = deepcopy(im_src)
        im_src2.shift(7, 7)
        im_src3 = deepcopy(im_src)
        im_src3.shift(-10, 14)
        im_src4 = deepcopy(im_src)
        im_src4.shift(-4, -6)
        im_src5 = deepcopy(im_src)
        im_src5.shift(15, -15)
        multi_img = im_src1 + im_src2 + im_src3 + im_src4 + im_src5

        cmds["SIM_PIXEL_SCALE"] = 0.02
        opt = OpticalTrain(cmds)
        opt.observe(multi_img)

        final_sum = np.sum(opt.image_plane.image)
        print(orig_sum, final_sum)

        if PLOTS:
            plt.imshow(opt.image_plane.image.T, origin="lower", norm=LogNorm())
            plt.colorbar()
            plt.show()

        assert final_sum == approx(5*orig_sum, rel=1e-3)
