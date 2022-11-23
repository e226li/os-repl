import logging
import paramiko
import sshim_patch as sshim
import lxd_interface
import os
import re

logging.basicConfig(level='DEBUG')
logger = logging.getLogger()


def connect_handler(script):
    # ask the SSH client to enter a name
    script.write('Please enter your name: ')

    # match their input against a regular expression which will store the name in a capturing group called name
    groups = script.expect(re.compile('(?P<name>.*)')).groupdict()

    # log on the server-side that the user has connected
    logger.info('%(name)s just connected', **groups)

    # send a message back to the SSH client greeting it by name
    script.writeline('Hello %(name)s!' % groups)


server = sshim.Server(connect_handler, address='0.0.0.0', port=3000)
try:
    server.run()
except KeyboardInterrupt:
    server.stop()
