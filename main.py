import logging
import paramiko
import sshim
import os
import re

# monkey patching


def check_auth_none(self, username):
    return paramiko.AUTH_PARTIALLY_SUCCESSFUL


def check_auth_password(self, username, password):
    if password == os.environ["ssh-password"]:
        return paramiko.AUTH_SUCCESSFUL
    return paramiko.AUTH_FAILED


def check_auth_publickey(self, username, key):
    return paramiko.AUTH_FAILED


def enable_auth_gssapi(self):
    return paramiko.AUTH_FAILED


sshim.Handler.check_auth_none = check_auth_none
sshim.Handler.check_auth_password = check_auth_password
sshim.Handler.check_auth_publickey = check_auth_publickey
sshim.Handler.enable_auth_gssapi = enable_auth_gssapi

# monkey patching complete

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
