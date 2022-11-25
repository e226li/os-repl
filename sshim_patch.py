from sshim import *
import paramiko
import os
import six
import codecs
import uuid
import lxd_interface
import threading
import logging

logging.basicConfig(level='DEBUG')
logger = logging.getLogger()


def expect(self, line, echo=True) -> str:
    """
        Expect a line of input from the user. If this has the `match` method, it will call it on the input and return
        the result, otherwise it will use the equality operator, ==. Notably, if a regular expression is passed in
        its match method will be called and the matchdata returned. This allows you to use matching groups to pull
        out interesting data and operate on it.
        If ``echo`` is set to False, the server will not echo the input back to the client.
    """
    buffer = six.BytesIO()

    try:
        while True:
            byte = self.fileobj.read(1)

            if not byte or byte == '\x04':
                raise EOFError()
            elif byte == b'\t':
                pass
            elif byte == b'\x7f':
                if buffer.tell() > 0:
                    self.sendall('\b \b')
                    buffer.truncate(buffer.tell() - 1)
            elif byte == b'\x1b' and self.fileobj.read(1) == b'[':
                command = self.fileobj.read(1)
                if hasattr(self.delegate, 'cursor'):
                    self.delegate.cursor(command)
            elif byte in (b'\r', b'\n'):
                break
            else:
                buffer.write(byte)
                if echo:
                    self.sendall(byte)

        if echo:
            self.sendall('\r\n')

        return codecs.decode(buffer.getvalue(), self.encoding)

    except Exception:
        raise


def check_channel_shell_request(self, channel):
    logger.debug(channel)
    Runner(self, channel).start()

    return True


def check_auth_none(self, username):
    if username == os.environ["ssh-username"]:
        return paramiko.AUTH_PARTIALLY_SUCCESSFUL
    return paramiko.AUTH_FAILED


def check_auth_password(self, username, password):
    print(os.environ["ssh-username"], os.environ["ssh-password"])
    if username == os.environ["ssh-username"] and password == os.environ["ssh-password"]:
        return paramiko.AUTH_SUCCESSFUL
    return paramiko.AUTH_FAILED


def check_auth_publickey(self, username, key):
    return paramiko.AUTH_FAILED


class Runner(threading.Thread):
    def __init__(self, client, channel: paramiko.Channel):
        threading.Thread.__init__(self, name='sshim.Runner(%s)' % channel.chanid)
        self.instance_name = "instance-" + str(uuid.uuid4())
        self.daemon = True
        self.client = client
        self.channel = channel
        self.channel.settimeout(None)

    def run(self) -> None:
        lxd_interface.create_instance(self.instance_name)

        with paramiko.ProxyCommand(command_line=f'lxc exec {self.instance_name} -- /bin/bash') as proxy_command:
            self.channel.recv = proxy_command.recv
            self.channel.send = proxy_command.send


Script.expect = expect

Handler.check_channel_shell_request = check_channel_shell_request
Handler.check_auth_none = check_auth_none
Handler.check_auth_password = check_auth_password
Handler.check_auth_publickey = check_auth_publickey
Handler.enable_auth_gssapi = paramiko.server.ServerInterface.enable_auth_gssapi
Handler.get_allowed_auths = paramiko.server.ServerInterface.get_allowed_auths
