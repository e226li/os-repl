from sshim import *
import paramiko
import os
import uuid
import lxd_interface
import threading
import logging
import select
import time
import inspect

logger = logging.getLogger(__name__)


def check_channel_shell_request(self, channel):
    logger.debug("Check channel shell request: %s" % channel.get_id())
    Runner(self, channel).start()

    return True


def check_auth_none(self, username):
    if username == os.environ["ssh-username"]:
        return paramiko.AUTH_PARTIALLY_SUCCESSFUL
    return paramiko.AUTH_FAILED


def check_auth_password(self, username, password):
    logger.debug(os.environ["ssh-username"])
    if username == os.environ["ssh-username"] and password == os.environ["ssh-password"]:
        return paramiko.AUTH_SUCCESSFUL
    return paramiko.AUTH_FAILED


def check_auth_publickey(self, username, key):
    return paramiko.AUTH_FAILED


class Runner(threading.Thread):
    def __init__(self, client, channel: paramiko.Channel):
        threading.Thread.__init__(self, name='sshim.Runner(%s)' % channel.chanid)
        self.instance_name = "instance-" + str(uuid.uuid4())
        self.instance_password = str(uuid.uuid4())  # TODO: secure password generation
        self.daemon = True
        self.client = client
        self.channel = channel
        self.channel.settimeout(None)
        self.transport = None

    def run(self) -> None:
        vm_ip = lxd_interface.create_instance(self.instance_name, self.instance_password)['address']

        with paramiko.SSHClient() as ssh_client:
            ssh_client.set_missing_host_key_policy(paramiko.WarningPolicy)
            ssh_client.connect(vm_ip, username='root', password=self.instance_password)
            self.transport = ssh_client.get_transport()
            client_channel = ssh_client.invoke_shell()

            while True:
                r, w, e = select.select([client_channel, self.channel], [], [])
                if self.channel in r:
                    x = self.channel.recv(1024)
                    if len(x) == 0:
                        break
                    client_channel.send(x)

                if client_channel in r:
                    x = client_channel.recv(1024)
                    if len(x) == 0:
                        break
                    self.channel.send(x)

            client_channel.close()
            self.channel.close()
            lxd_interface.destroy_instance(self.instance_name)


Handler.check_channel_shell_request = check_channel_shell_request
Handler.check_auth_none = check_auth_none
Handler.check_auth_password = check_auth_password
Handler.check_auth_publickey = check_auth_publickey
Handler.enable_auth_gssapi = paramiko.server.ServerInterface.enable_auth_gssapi
Handler.get_allowed_auths = paramiko.server.ServerInterface.get_allowed_auths
