import numpy as np
from astropy import units as u
from astropy.table import Table

from .effects import Effect
from .apertures import ApertureMask
from .. import utils
from ..optics.image_plane_utils import header_from_list_of_xy, calc_footprint

__all__ = ["DetectorList", "DetectorWindow"]


class DetectorList(Effect):
    """

    Examples
    --------
    ::
        - name : full_detector
          class : DetectorList
          kwargs :
            filename : "FPA_array_layout.dat"
            active_detectors : [1, 5]

    """

    def __init__(self, **kwargs):
        super(DetectorList, self).__init__(**kwargs)
        self.meta["z_order"] = [90, 290, 390, 490]
        self.meta["pixel_scale"] = "!INST.pixel_scale"      # arcsec
        self.meta["active_detectors"] = "all"
        self.meta.update(kwargs)

    def fov_grid(self, which="edges", **kwargs):
        """Returns an ApertureMask object. kwargs are "pixel_scale" [arcsec]"""
        aperture_mask = None
        if which == "edges":
            self.meta.update(kwargs)
            self.meta = utils.from_currsys(self.meta)

            hdr = self.image_plane_header
            x_mm, y_mm = calc_footprint(hdr, "D")
            pixel_size = hdr["CDELT1D"]              # mm
            pixel_scale = self.meta["pixel_scale"]   # ["]
            x_sky = x_mm * pixel_scale / pixel_size  # x["] = x[mm] * ["] / [mm]
            y_sky = y_mm * pixel_scale / pixel_size  # y["] = y[mm] * ["] / [mm]

            aperture_mask = ApertureMask(array_dict={"x": x_sky, "y": y_sky},
                                         pixel_scale=pixel_scale)

        return aperture_mask

    @property
    def image_plane_header(self):
        tbl = self.active_table
        pixel_size = np.min(utils.quantity_from_table("pixsize", tbl, u.mm))
        x_unit = utils.unit_from_table("x_cen", tbl, u.mm)
        y_unit = utils.unit_from_table("y_cen", tbl, u.mm)

        x_det_min = np.min(tbl["x_cen"] - tbl["xhw"]) * x_unit
        x_det_max = np.max(tbl["x_cen"] + tbl["xhw"]) * x_unit
        y_det_min = np.min(tbl["y_cen"] - tbl["yhw"]) * y_unit
        y_det_max = np.max(tbl["y_cen"] + tbl["yhw"]) * y_unit

        x_det = [x_det_min.to(u.mm).value, x_det_max.to(u.mm).value]
        y_det = [y_det_min.to(u.mm).value, y_det_max.to(u.mm).value]

        pixel_size = pixel_size.to(u.mm).value
        hdr = header_from_list_of_xy(x_det, y_det, pixel_size, "D")
        hdr["IMGPLANE"] = self.meta["image_plane_id"]

        return hdr

    @property
    def active_table(self):
        if self.meta["active_detectors"] == "all":
            tbl = self.table
        elif isinstance(self.meta["active_detectors"], (list, tuple)):
            mask = [det_id in self.meta["active_detectors"]
                    for det_id in self.table["id"]]
            tbl = self.table[mask]
        else:
            raise ValueError("Could not determine which detectors are active: "
                             "{}, {}, ".format(self.meta["active_detectors"],
                                               self.table))
        return tbl

    def detector_headers(self, ids=None):
        if ids is not None and all([isinstance(ii, int) for ii in ids]):
            self.meta["active_detectors"] = list(ids)

        hdrs = []
        for row in self.active_table:
            xcen, ycen = row["x_cen"], row["y_cen"]
            dx, dy = row["xhw"], row["yhw"]
            cdelt = row["pixsize"]

            hdr = header_from_list_of_xy([xcen-dx, xcen+dx], [ycen-dy, ycen+dy],
                                         pixel_scale=cdelt, wcs_suffix="D")
            if abs(row["angle"]) > 1E-4:
                sang = np.sin(row["angle"] / 57.29578)
                cang = np.cos(row["angle"] / 57.29578)
                hdr["PC1_1"] = cang
                hdr["PC1_2"] = sang
                hdr["PC2_1"] = -sang
                hdr["PC2_2"] = cang

            # hdr["GAIN"] = row["gain"]
            # if "id" in row:
            #     hdr["ID"] = row["id"]
            row_dict = {col: row[col] for col in row.colnames}
            hdr.update(row_dict)
            hdrs += [hdr]

        return hdrs

    def plot(self):
        import matplotlib.pyplot as plt

        for hdr in self.detector_headers():
            x_mm, y_mm = calc_footprint(hdr, "D")
            x_cen, y_cen = np.average(x_mm), np.average(y_mm)
            x_mm = list(x_mm) + [x_mm[0]]
            y_mm = list(y_mm) + [y_mm[0]]
            plt.plot(x_mm, y_mm)
            plt.text(x_cen, y_cen, hdr["ID"])

        plt.gca().set_aspect("equal")


class DetectorWindow(DetectorList):
    """
    For when a full DetectorList if too cumbersome

    Parameters
    ----------
    pixel_size : float
        [mm / pix] Physical pixel size
    x, y : float
        [mm] Position of window centre relative to optical axis
    width, height=None : float
        [mm] Dimensions of window. If height is None, height=width
    angle : float, optional
        [deg] Rotation of window
    gain : float, optional
        [ADU/e-]

    """
    def __init__(self, pixel_size, x, y, width, height=None, angle=0, gain=1,
                 **kwargs):
        if height is None:
            height = width
        tbl = Table(data=[[0], [x], [y], [width / 2.], [height / 2.],
                          [angle], [gain], [pixel_size]],
                    names=["id", "x_cen", "y_cen", "xhw", "yhw",
                           "angle", "gain", "pixsize"])
        if "image_plane_id" not in kwargs:
            kwargs["image_plane_id"] = 0

        super(DetectorWindow, self).__init__(table=tbl, **kwargs)
