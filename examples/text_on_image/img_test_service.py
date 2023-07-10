#
# Copyright (c) 2023 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
import sys, os
SCRIPT_DIR=os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(SCRIPT_DIR, '../../src'))

import logging
from PIL import Image, ImageDraw, ImageFont

from ivcap_sdk_service import Service, Parameter, Type, SupportedMimeTypes, ServiceArgs
from ivcap_sdk_service import register_service, deliver_data, fetch_data, create_metadata

logger = None # set when called by SDK

SERVICE = Service(
    name = "simple-python-service",
    description = "A simple IVCAP service using the IVCAP Service SDK to create an image with text overlays",
    parameters = [
        Parameter(
            name='msg', 
            type=Type.STRING, 
            description='Message to display.'),
         Parameter(
            name='backgrounds', 
            type=Type.COLLECTION, 
            description='Create a new result for every image in collection.',
            optional=True),
       Parameter(
            name='bg-artifact', 
            type=Type.ARTIFACT, 
            description='Image artifact to use as background.',
            optional=True),
        Parameter(
            name='width', 
            type=Type.INT, 
            description='Image width.',
            default=640),
        Parameter(
            name='height', 
            type=Type.INT, 
            description='Image height.',
            default=480),
        Parameter(
            name='transparent-background', 
            type=Type.BOOL, 
            description='Indicate transparent background image(s)'),
    ]
)

def create_img(count: int, msg: str, width: int, height: int, bg_img, bg_transparent: bool):
    # Create an image
    img = Image.new("RGBA", (width, height), "white")
    
    # Add background
    if bg_img:
        background = Image.open(bg_img)
        if bg_transparent:
            img.paste(background, mask=background)
        else:
            img.paste(background)
    
    # Draw message
    canvas = ImageDraw.Draw(img)
    font = ImageFont.truetype(os.path.join(SCRIPT_DIR, 'CaveatBrush-Regular.ttf'), 100)
    center = (width / 2, height / 2)
    canvas.text(center, msg, font=font, anchor='mm', fill=(255, 130, 0))   
    
    md = {
        'msg': msg,
        'width': width,
        'height': height,
    }
    if bg_img:
        md['background'] = bg_img 
    meta = create_metadata('urn:testing:schema:simple-python-service', md)
    deliver_data(f'image.{count}.png', lambda fd: img.save(fd, format="png"), SupportedMimeTypes.JPEG, metadata=meta)

def service(args: ServiceArgs, svc_logger: logging):
    global logger 
    logger = svc_logger
    
    bg_tran = args.transparent_background
    if args.backgrounds:
        for count, bg in enumerate(args.backgrounds):
            count += 1
            create_img(count, args.msg, args.width, args.height, bg, bg_tran)
    else:
        create_img(0, args.msg, args.width, args.height, args.bg_artifact, bg_tran)
    
register_service(SERVICE, service)
