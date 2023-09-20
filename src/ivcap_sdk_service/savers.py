#
# Copyright (c) 2023 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
from typing import Any

from .ivcap import register_saver
from .itypes import SupportedMimeTypes
from .cio.io_adapter import IOAdapter, IOWritable


def xa_dataset_saver(name: str, data: Any, io_adapter: IOAdapter, **kwargs):
    """
    Saves an xarray dataset to a NetCDF file using the provided IOAdapter.

    Args:
        name (str): The name of the file to be saved.
        data (Any): The xarray dataset to be saved.
        io_adapter (IOAdapter): The IOAdapter to use for writing the file.
        **kwargs: Additional keyword arguments to be passed to the IOAdapter.

    Returns:
        None
    """
    kwargs["seekable"] = True
    xmeta = data.to_dict(data=False)
    xmeta["@schema"] = "urn:schema:xarray"
    _append_meta(kwargs, xmeta)
    fhdl: IOWritable = io_adapter.write_artifact(
        SupportedMimeTypes.NETCDF, f"{name}.nc", **kwargs
    )
    data.to_netcdf(fhdl, compute=True)
    fhdl.close()


def png_pil_saver(name: str, img: Any, io_adapter: IOAdapter, **kwargs):
    """
    Saves a PIL image as a PNG file using the provided IOAdapter.

    Args:
        name (str): The name of the file to save.
        img (Any): The PIL image to save.
        io_adapter (IOAdapter): The IOAdapter to use for saving the file.
        **kwargs: Additional keyword arguments to pass to the IOAdapter.

    Returns:
        None
    """
    _pil_saver(name, img, SupportedMimeTypes.PNG, "png", io_adapter, kwargs)


def jpeg_pil_saver(name: str, img: Any, io_adapter: IOAdapter, **kwargs):
    """
    Saves a PIL image as a JPEG file.

    Args:
        name (str): The name of the file to save.
        img (Any): The PIL image to save.
        io_adapter (IOAdapter): The IOAdapter instance to use for saving the file.
        **kwargs: Additional keyword arguments to pass to the PIL save method.

    Returns:
        None
    """
    _pil_saver(name, img, SupportedMimeTypes.JPEG, "jpeg", io_adapter, kwargs)


def _pil_saver(
    name: str,
    img: Any,
    mtype: SupportedMimeTypes,
    img_format: str,
    io_adapter: IOAdapter,
    kwargs,
):
    """
    Saves a PIL image to an artifact using the provided IOAdapter.

    Args:
        name (str): The name of the image.
        img (Any): The PIL image to save.
        mtype (SupportedMimeTypes): The MIME type of the image.
        img_format (str): The format to save the image in.
        io_adapter (IOAdapter): The IOAdapter to use for writing the artifact.
        kwargs: Additional keyword arguments to pass to the IOAdapter.

    Returns:
        None
    """
    kwargs["seekable"] = False
    _append_meta(
        kwargs,
        {
            "@schema": "urn:schema:image",
            "name": name,
            "width": img.width,
            "height": img.height,
            "format": img_format,
        },
    )
    fhdl: IOWritable = io_adapter.write_artifact(
        mtype, f"{name}.{img_format}", **kwargs
    )
    img.save(fhdl, format="png")
    fhdl.close()


def _append_meta(kwargs, meta):
    """
    Append metadata to the given keyword arguments.

    :param kwargs: The keyword arguments to append metadata to.
    :type kwargs: dict
    :param meta: The metadata to append.
    :type meta: Any
    """
    mdl = kwargs.get("metadata", [])
    if not isinstance(mdl, list):
        mdl = [mdl]
    mdl.append(meta)
    kwargs["metadata"] = mdl


def register_savers():
    """
    Registers savers for supported MIME types and data types.

    Supported MIME types include NETCDF, PNG, and JPEG. Supported data types include xarray Dataset and DataArray,
    as well as PIL Image. The savers are registered using the `register_saver` function, which takes the MIME type,
    data type, and corresponding saver function as arguments.
    """
    register_saver(
        SupportedMimeTypes.NETCDF,
        "<class 'xarray.core.dataset.Dataset'>",
        xa_dataset_saver,
    )
    register_saver(
        SupportedMimeTypes.NETCDF,
        "<class 'xarray.core.dataarray.DataArray'>",
        xa_dataset_saver,
    )

    register_saver(SupportedMimeTypes.PNG, "<class 'PIL.Image.Image'>", png_pil_saver)
    register_saver(SupportedMimeTypes.JPEG, "<class 'PIL.Image.Image'>", jpeg_pil_saver)
