from sshim import *
import pylxd
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


def check_channel_request(self, kind, channel_id):
    logger.debug(f"Client requested {kind}")
    if kind in ('session', 'sftp'):
        return paramiko.OPEN_SUCCEEDED
    return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED


def check_channel_shell_request(self, channel):
    logger.debug("Check channel shell request: %s" % channel.get_id())
    self.runner.set_shell_channel(channel)

    return True


def check_channel_subsystem_request(self, channel, name):
    if name == 'sftp':
        self.runner.set_sftp_channel(channel)
        return True
    else:
        return False


def check_auth_none(self, username):
    if username == os.environ["SSH_USERNAME"]:
        return paramiko.AUTH_PARTIALLY_SUCCESSFUL
    return paramiko.AUTH_FAILED


def check_auth_password(self, username, password):
    logger.debug(f"{username} just tried to connect")
    if username == os.environ["SSH_USERNAME"] and password == os.environ["SSH_PASSWORD"]:
        self.runner = Runner(self, os.environ["SSH_USERNAME"], self.transport)
        self.runner.start()
        return paramiko.AUTH_SUCCESSFUL
    return paramiko.AUTH_FAILED


def check_auth_publickey(self, username, key):
    return paramiko.AUTH_FAILED


class Runner(threading.Thread):
    def __init__(self, client, username: str, transport: paramiko.Transport, start_instance: bool = True):
        self.instance_name = "instance-" + username
        self.runner_identifier = "runner-" + str(uuid.uuid4())
        threading.Thread.__init__(self, name=f'sshim.Runner {self.instance_name} {self.runner_identifier}')
        self.instance_password = self.instance_name  # TODO: fix - VERY INSECURE!
        self.daemon = True
        self.client = client
        self.transport = transport
        self.start_instance = start_instance
        self.shell_channel = None
        self.sftp_channel = None

    def run(self) -> None:
        try:
            vm_ip = lxd_interface.create_instance(self.instance_name, self.instance_password)['address']
        except pylxd.exceptions.LXDAPIException as e:
            logger.debug(e)
            vm_ip = lxd_interface.get_networking(self.instance_name)['address']

        with paramiko.SSHClient() as ssh_client:
            ssh_client.set_missing_host_key_policy(paramiko.WarningPolicy)
            ssh_client.connect(vm_ip, username='root', password=self.instance_password)
            client_shell_channel = ssh_client.invoke_shell()
            client_sftp_channel = ssh_client.open_sftp().get_channel()

            last_save_time = round(time.time())
            while True:
                current_time_rounded = round(time.time())
                if current_time_rounded != last_save_time:
                    lxd_interface.set_description(self.instance_name, str(current_time_rounded))
                    last_save_time = current_time_rounded

                if self.shell_channel is not None:
                    r, w, e = select.select([client_shell_channel, self.shell_channel], [], [])
                    if self.shell_channel in r:
                        x = self.shell_channel.recv(1024)
                        if len(x) == 0:
                            self.shell_channel.close()
                            self.shell_channel = None
                            break
                        client_shell_channel.send(x)
                    if client_shell_channel in r:
                        x = client_shell_channel.recv(1024)
                        if len(x) == 0:
                            self.shell_channel.close()
                            self.shell_channel = None
                            break
                        self.shell_channel.send(x)

                if self.sftp_channel is not None:  # TODO: move this to function
                    r, w, e = select.select([client_sftp_channel, self.sftp_channel], [], [])
                    if self.sftp_channel in r:
                        x = self.sftp_channel.recv(1024)
                        if len(x) == 0:
                            self.sftp_channel.close()
                            self.sftp_channel = None
                            break
                        client_sftp_channel.send(x)
                    if client_sftp_channel in r:
                        x = client_sftp_channel.recv(1024)
                        if len(x) == 0:
                            self.sftp_channel.close()
                            self.sftp_channel = None
                            break
                        self.sftp_channel.send(x)

                if self.transport.is_active() is False:
                    break

            exit_time = round(time.time())
            time.sleep(10)
            while True:
                last_run_time = int(lxd_interface.get_description(self.instance_name))

                if exit_time < last_run_time:
                    break
                elif round(time.time()) > (last_run_time + 15):
                    lxd_interface.destroy_instance(self.instance_name)
                    break

    def set_shell_channel(self, channel):
        self.shell_channel = channel
        self.shell_channel.settimeout(None)

    def set_sftp_channel(self, channel):
        self.sftp_channel = channel
        self.sftp_channel.settimeout(None)


Handler.check_channel_request = check_channel_request
Handler.check_channel_shell_request = check_channel_shell_request
Handler.check_channel_subsystem_request = check_channel_subsystem_request
Handler.check_auth_none = check_auth_none
Handler.check_auth_password = check_auth_password
Handler.check_auth_publickey = check_auth_publickey
Handler.enable_auth_gssapi = paramiko.server.ServerInterface.enable_auth_gssapi
Handler.get_allowed_auths = paramiko.server.ServerInterface.get_allowed_auths
