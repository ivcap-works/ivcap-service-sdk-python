#
# Copyright (c) 2023 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
import base64
from dataclasses import dataclass
import os
from argparse import ArgumentParser, ArgumentTypeError
from pathlib import Path
from typing import MutableSequence, Callable, Dict
import sys

from enum import Enum, auto

from .cio import IOAdapter, LocalIOAdapter, IvcapIOAdapter, Cache
from .logger import sys_logger as logger

INSIDE_CONTAINER = not not os.getenv('IVCAP_INSIDE_CONTAINER', None) # make it a bool
INSIDE_ARGO = not not os.getenv('ARGO_NODE_ID', None) # make it a bool

DEF_OUT_DIR = '/data/out'
DEF_IN_DIR = '/data/in'

DEF_CACHE_DIR = '/cache'
DEF_SCHEMA_PREFIX = 'urn:ivcap:'

SUPPORTED_PROTOCOLS = ['httpserver', 'opendap']

class Command(Enum):
    SERVICE_RUN = auto()
    SERVICE_HELP = auto()
    SERVICE_FILE = auto()

class Resource(Enum):
    ORDER = 'order'
    SERVICE = 'service'
    ARTIFACT = 'artifact'  
    COLLECTION = 'collection'
    ACCOUNT = 'account'

@dataclass(init=False)
class Config:
  ORDER_ID: str
  NODE_ID: str

  IO_ADAPTER: IOAdapter
  CACHE: Cache
  CACHE_PROXY_URL: str
  STORAGE_URL: str
  OUT_DIR: str

  SCHEMA_PREFIX: str
  QUEUE_PREFIX: str  
  
  SERVICE_ARGS: MutableSequence[str]
  SERVICE_COMMAND: Command = Command.SERVICE_RUN


  def __init__(self, argv:Dict[str, str] = None, modify_ap: Callable[[ArgumentParser], ArgumentParser] = None):
    prog = os.path.basename(sys.argv[0])
    if prog == '__main__.py' or prog == '-m':
        prog = self._def_prog_name()

    ap = ArgumentParser(prog=prog, description='Execute a service to create information products.')
    self.add_arguments(ap)

    if argv is None:
        argv = getProgramArgs()
    pargs, self.SERVICE_ARGS = ap.parse_known_args(argv)
    args = vars(pargs)

    self._set(args)

  def _def_prog_name(self):
    return "ivcap-service"

  def _set(self, args):
    order_id_def = os.getenv('IVCAP_ORDER_ID')
    node_id_def = os.getenv('ARGO_NODE_ID')

    if args.pop('ivcap:service_help', False):
        self.SERVICE_COMMAND = Command.SERVICE_HELP
    elif args.pop('ivcap:print_service_description', False):
        self.SERVICE_COMMAND = Command.SERVICE_FILE

    self.ORDER_ID = args.pop('ivcap:order_id', order_id_def)
    if not self.ORDER_ID:
        self.ORDER_ID = "urn:ivcap:order:00000000-0000-0000-0000-000000000000"
        if INSIDE_ARGO:
            logger.warn("missing 'order-id'")
        
    self.NODE_ID = args.pop('ivcap:node_id', node_id_def)

    self.CACHE_PROXY_URL = args.pop('ivcap:cache_proxy', None)
    cacheDir = args.pop('ivcap:cache_dir', None)
    if cacheDir != '':
        self.CACHE = Cache(cache_dir=cacheDir)
    else:
        self.CACHE = None

    self.STORAGE_URL = args.pop('ivcap:storage_url', None)
    in_dir = args.pop('ivcap:in_dir', None)
    self.OUT_DIR = args.pop('ivcap:out_dir', DEF_OUT_DIR)
    if self.STORAGE_URL:
      self.IO_ADAPTER = IvcapIOAdapter(
        storage_url = self.STORAGE_URL,
        in_dir = in_dir,
        out_dir = self.OUT_DIR,
        order_id=self.ORDER_ID,
        #cache = self.CACHE,
        cachable_url = self.cachable_url,
       )
    else:
      self.IO_ADAPTER = LocalIOAdapter(in_dir=in_dir, out_dir=self.OUT_DIR, cache_dir=cacheDir)

    self.SCHEMA_PREFIX = args.pop('ivcap:schema_prefix', None)
    self.QUEUE_PREFIX = f"{self.SCHEMA_PREFIX}queue:"
    
  def add_arguments(self, ap):
    order_id_def = os.getenv('IVCAP_ORDER_ID')
    node_id_def = os.getenv('ARGO_NODE_ID')

    out_dir_def=os.getenv('IVCAP_OUT_DIR', DEF_OUT_DIR if INSIDE_CONTAINER else '.')
    in_dir_def=os.getenv('IVCAP_IN_DIR', DEF_IN_DIR if INSIDE_CONTAINER else '.')

    cache_dir_def=os.getenv('IVCAP_CACHE_DIR')
    if cache_dir_def == None:
        if INSIDE_CONTAINER:
            cache_dir_def = DEF_CACHE_DIR
        else:
            cache_dir_def = os.path.join(os.getcwd(), 'cache')
    cache_proxy_def=os.getenv('IVCAP_CACHE_URL')

    schema_prefix_def = os.getenv('IVCAP_SCHEMA_PREFIX', DEF_SCHEMA_PREFIX)

    storage_url_def = os.getenv('IVCAP_STORAGE_URL', None)

    ap.add_argument("-H", "--ivcap:service-help",
        action='store_true',
        help="Show service help")

    ap.add_argument("--ivcap:print-service-description",
        action='store_true',
        help="Print service description")

    ap.add_argument("--ivcap:order-id", metavar="ID", 
        help=f"Order ID [IVCAP_ORDER_ID={order_id_def}]",
        default=order_id_def,
        required=INSIDE_CONTAINER and not order_id_def)
    ap.add_argument("--ivcap:node-id", metavar="ID", 
        help=f"Execution node ID [ARGO_NODE_ID={node_id_def}]",
        default=node_id_def)
    ap.add_argument("--ivcap:out-dir", metavar="DIR", 
        help=f"Directory to place results into [IVCAP_OUT_DIR={out_dir_def}]",
        default=out_dir_def,
        type=verify_dir)
    ap.add_argument("--ivcap:in-dir", metavar="DIR", 
        help=f"Directory to fetch local data from [IVCAP_IN_DIR={in_dir_def}]",
        default=in_dir_def,
        type=verify_dir)

    ap.add_argument("--ivcap:cache-dir", metavar="DIR", 
        help=f"Directory to locally cache files [IVCAP_CACHE_DIR={cache_dir_def}]",
        default=cache_dir_def)
    ap.add_argument("--ivcap:cache-proxy", metavar="URL", 
        help=f"Cache proxy url [IVCAP_CACHE_PROXY={cache_proxy_def}]",
        default=cache_proxy_def)

    ap.add_argument("--ivcap:storage-url", metavar="URL", 
        help=f"URL to simple storage provider [IVCAP_STORAGE_URL={storage_url_def}]",
        default=storage_url_def)

    ap.add_argument("--ivcap:schema-prefix", metavar="INT", 
        help=f"Schema prefix to use [IVCAP_SCHEMA_PREFIX={schema_prefix_def}]",
        default=schema_prefix_def)

    ap.add_argument("--print-config",
        action='store_true',
        help="Print config settings and exit")      

  def cachable_url(self, url: str) -> str:
    """Modify url if there is a cache proxy available"""

    def combine(u1, u2): 
        if u1.endswith("/"):
            curl = u1 + u2
        else:
            curl = f"{u1}/{u2}"
        return curl    

    if url.startswith(self.SCHEMA_PREFIX):
        return combine(self.STORAGE_URL, url)

    if self.CACHE_PROXY_URL == None:
        return url
    # Call CACHE_PROXY_URL with base64 encoded url as path
    p = base64.urlsafe_b64encode(url.encode('utf-8')).decode('ascii')
    # data-proxy doesn't like trailing '='
    while p.endswith("="): p = p[:-1]
    return combine(self.CACHE_PROXY_URL, p)

def verify_file(fname):
  if Path(fname).is_file():
      return fname
  else:
      raise ArgumentTypeError(f"Can't find file '{fname}'")

def verify_dir(dname):
  if Path(dname).is_dir():
      return dname
  else:
      raise ArgumentTypeError(f"Can't find directory '{dname}'")

def verify_protocol(fname):
  if fname.lower() in SUPPORTED_PROTOCOLS:
    return fname.lower()
  else:
    raise ArgumentTypeError(f"Protocol '{fname}' is not in supported list '{', '.join(SUPPORTED_PROTOCOLS)}'.")

def getProgramArgs():
  if os.getenv('IVCAP_ENV0') == None:
    return sys.argv[1:]

  argv = []
  i = 0
  v = os.getenv(f"IVCAP_ENV{i}")
  while (v != None):
    argv.append(v)
    i += 1
    v = os.getenv(f"IVCAP_ENV{i}")
  return argv

def storeConfigInEnv():
  i = 0
  for v in getProgramArgs():
    os.environ[f'IVCAP_ENV{i}'] = v
    i += 1
