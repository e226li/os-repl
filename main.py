import logging
import time
import paramiko
import sshim_patch as sshim
import lxd_interface
import os
import re
import uuid

logging.basicConfig(level='DEBUG')
logger = logging.getLogger()


def connect_handler(script: sshim.Script):
    pass


server = sshim.Server(connect_handler, address='127.0.0.1', port=3022)
try:
    server.run()
except KeyboardInterrupt:
    server.stop()
finally:
    lxd_interface.destroy_all_instances()
