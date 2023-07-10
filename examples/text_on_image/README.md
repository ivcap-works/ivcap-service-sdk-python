<!--
Copyright (c) 2023 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
Use of this source code is governed by a BSD-style license that can be
found in the LICENSE file. See the AUTHORS file for names of contributors.
-->
# Example: Image with Text and Background Image

This directory implements a simple service which produces
an image with a configurable text message and an optional
background image.

The background image can either be a URL or an IVCAP artifact urn.

If the `--backgrounds` property refers to a _collection_ than a
separate image is produced for every background image in that
collection.

Please note, that in _local_ mode, if `--backgrounds` refers to
a directory, than every file in that directory is assumed to be
part of the collection.

Please see the [Makefile](./Makefile) for the various ways to
execute this service.
