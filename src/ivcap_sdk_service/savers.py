#
# Copyright (c) 2023 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
from .ivcap import register_saver
from .itypes import SupportedMimeTypes
from typing import Any
from .cio.io_adapter import IOAdapter, IOWritable

def xa_dataset_saver(name: str, data: Any, io_adapter: IOAdapter, **kwargs):
    kwargs['seekable'] = True
    xmeta = data.to_dict(data=False)
    xmeta['@schema'] = 'urn:schema:xarray'
    _append_meta(kwargs, xmeta)
    fhdl: IOWritable = io_adapter.write_artifact(SupportedMimeTypes.NETCDF, f"{name}.nc", **kwargs)
    data.to_netcdf(fhdl, compute=True)
    fhdl.close()

def png_pil_saver(name: str, img: Any, io_adapter: IOAdapter, **kwargs):
    _pil_saver(name, img, SupportedMimeTypes.PNG, 'png', io_adapter, kwargs)

def jpeg_pil_saver(name: str, img: Any, io_adapter: IOAdapter, **kwargs):
    _pil_saver(name, img, SupportedMimeTypes.JPEG, 'jpeg', io_adapter, kwargs)

def _pil_saver(name: str, img: Any, mtype: SupportedMimeTypes, format: str, io_adapter: IOAdapter, kwargs):
    kwargs['seekable'] = False
    _append_meta(kwargs, {
        '@schema': 'urn:schema:image',
        'name': name,
        'width': img.width,
        'height': img.height,
        'format': format,
    })
    fhdl: IOWritable = io_adapter.write_artifact(mtype, f"{name}.{format}", **kwargs)
    img.save(fhdl, format="png")
    fhdl.close()

def _append_meta(kwargs, meta):
    mdl = kwargs.get('metadata', [])
    if not isinstance(mdl, list):
        mdl = [mdl]
    mdl.append(meta)
    kwargs['metadata'] = mdl

def register_savers():
    register_saver(SupportedMimeTypes.NETCDF, "<class 'xarray.core.dataset.Dataset'>", xa_dataset_saver)
    register_saver(SupportedMimeTypes.NETCDF, "<class 'xarray.core.dataarray.DataArray'>", xa_dataset_saver)

    register_saver(SupportedMimeTypes.PNG, "<class 'PIL.Image.Image'>", png_pil_saver)
    register_saver(SupportedMimeTypes.JPEG, "<class 'PIL.Image.Image'>", jpeg_pil_saver)

