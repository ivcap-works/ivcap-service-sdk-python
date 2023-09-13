# import docker
import os
import logging
import subprocess

from ivcap_sdk_service import Service, Parameter, Type, PythonWorkflow, ServiceArgs, SupportedMimeTypes
from ivcap_sdk_service import register_service, create_metadata, publish_artifact
from PIL import Image
from tempfile import TemporaryDirectory

logger = None # set when called by SDK

SERVICE = Service(
    description = 'Reproduce images with geometric primitives.',
    name = 'primitive',
    parameters = [
        Parameter(
            description =  'input file',
            type =  Type.ARTIFACT,
            name = 'input_image',
            optional =  False
        )
        # Parameter(
        #     name = 'n',
        #     description =  'number of shapes',
        #     type =  Type.INT,
        #     default =  100,
        #     optional =  True
        # ),
        # Parameter(
        #     name = 'm',
        #     description =  'mode: 0=combo, 1=triangle, 2=rect, 3=ellipse, 4=circle, 5=rotatedrect, 6=beziers, 7=rotatedellipse, 8=polygon',
        #     type =  Type.INT,
        #     default =  1,
        #     optional =  True
        # ),
        # Parameter(
        #     name = 'rep',
        #     description =  'add N extra shapes each iteration with reduced search (mostly good for beziers)',
        #     type =  Type.INT,
        #     default =  0,
        #     optional =  True
        # ),
        # Parameter(
        #     name = 'nth',
        #     description =  'save every Nth frame (only when %d is in output path)',
        #     type =  Type.INT,
        #     default =  1,
        #     optional =  True
        # ),
        # Parameter(
        #     name = 'r',
        #     description =  'resize large input images to this size before processing',
        #     type =  Type.INT,
        #     default =  256,
        #     optional =  True
        # ),
        # Parameter(
        #     name = 's',
        #     description =  'output image size',
        #     type =  Type.INT,
        #     default =  1024,
        #     optional =  True
        # ),
        # Parameter(
        #     name = 'a',
        #     description =  'color alpha (use 0 to let the algorithm choose alpha for each shape)',
        #     type =  Type.INT,
        #     default =  128,
        #     optional =  True
        # ),
        # Parameter(
        #     name = 'bg',
        #     description =  'starting background color (hex)',
        #     type =  Type.STRING,
        #     default =  'avg',
        #     optional =  True
        # ),
        # Parameter(
        #     name = 'j',
        #     description =  'number of parallel workers (default uses all cores)',
        #     type =  Type.INT,
        #     default =  0,
        #     optional =  True
        # )
    ],
    workflow=PythonWorkflow(script='/primitive/service.py', min_memory='2Gi')
)

def service(args: ServiceArgs, svc_logger: logging):
    global logger 
    logger = svc_logger

    logger.info(f"Called with {args}")
    input_image = Image.open(args.input_image)


    with TemporaryDirectory() as tmpdir:
        logger.info(f"Using temporary directory {tmpdir}")

        logger.info(f"Creating input and output directories")
        os.mkdir(os.path.join(tmpdir, 'input'))
        os.mkdir(os.path.join(tmpdir, 'output'))

        logger.info(f"Saving input image")
        input_image_path = os.path.join(tmpdir, 'input.jpg')
        input_image.save(input_image_path)
        
        output_image_path = os.path.join(tmpdir, 'output.jpg')

        # Define the command as a list of strings
        logger.info('Generating primitive command')
        command = ['primitive', '-i', input_image_path, '-o', output_image_path, '-n', '100']

        # Use subprocess.run() to execute the command
        logger.info(f'Running command via subprocess: {command}')
        result = subprocess.run(command, stdout=subprocess.PIPE)

        # Print the output of the command
        logger.info(f"Primitive output: \n{result.stdout.decode()}")

        logger.info(f"Creating metadata {output_image_path}")
        
        logger.info(f"Publishing output image {output_image_path}")
        publish_artifact(
            f'{output_image_path}', 
            lambda buffer: buffer.write(open(output_image_path, "rb").read()),
            SupportedMimeTypes.JPEG) 

register_service(SERVICE, service)
