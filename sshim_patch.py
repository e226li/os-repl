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
import ipaddress
import secrets
import inspect

logger = logging.getLogger(__name__)


def check_channel_request(self, kind, channel_id):
    logger.debug(f"Client requested {kind}")
    if kind in ('session', 'sftp'):
        return paramiko.OPEN_SUCCEEDED
    return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED


def check_channel_shell_request(self, channel):
    logger.debug("Check channel shell request: %s" % channel.get_id())
    Runner(self, self.username, 'shell', channel).start()

    return True


def check_channel_exec_request(self, channel):
    logger.debug("Check channel exec request: %s" % channel.get_id())
    Runner(self, self.username, 'exec', channel).start()

    return True


def check_channel_subsystem_request(self, channel, name):
    if name == 'sftp':
        Runner(self, self.username, 'sftp', channel).start()
        return True
    else:
        return False


def check_auth_none(self, username):
    return paramiko.AUTH_FAILED


def check_auth_password(self, username, password):
    logger.debug(f"{username} just tried to connect")
    # ensure that the connection is made from a local ip
    if ipaddress.ip_address(self.address).is_private is not True:
        return paramiko.AUTH_FAILED
    if secrets.compare_digest(password, os.environ["SSH_PASSWORD"]):
        self.username = username
        Runner(self, self.username).start()
        return paramiko.AUTH_SUCCESSFUL
    return paramiko.AUTH_FAILED


def check_auth_publickey(self, username, key):
    return paramiko.AUTH_FAILED


class Runner(threading.Thread):
    def __init__(self, client, username: str, channel_type: str = None, channel: paramiko.Channel = None):
        self.instance_name = "instance-" + username
        self.runner_identifier = "runner-" + str(uuid.uuid4())
        threading.Thread.__init__(self, name=f'sshim.Runner {self.instance_name} {self.runner_identifier}')
        self.instance_password = self.instance_name  # TODO: fix - VERY INSECURE!
        self.daemon = True
        self.client = client
        self.channel_type = channel_type
        self.channel = channel

    def run(self) -> None:
        try:
            vm_ip = lxd_interface.create_instance(self.instance_name, self.instance_password)['address']
        except pylxd.exceptions.LXDAPIException as e:
            logger.debug(e)
            vm_ip = lxd_interface.get_networking(self.instance_name)['address']

        if self.channel is not None:
            self.channel.get_transport().set_keepalive(5)  # TODO: make config option

        with paramiko.SSHClient() as ssh_client:
            # wait for instance to start if it hasn't started yet
            is_not_int = True
            while is_not_int and self.channel is not None:
                try:
                    int(lxd_interface.get_description(self.instance_name))
                    is_not_int = False
                except ValueError as e:
                    logger.debug(e)
                    time.sleep(0.2)

            ssh_client.set_missing_host_key_policy(paramiko.WarningPolicy)
            ssh_client.connect(vm_ip, username='root', password=self.instance_password)
            if self.channel_type == "shell" or self.channel_type == "exec":
                client_channel = ssh_client.invoke_shell()
            elif self.channel_type == "sftp":
                client_channel = ssh_client.open_sftp().get_channel()

            last_save_time = round(time.time())
            lxd_interface.set_description(self.instance_name, str(last_save_time))
            forward_channel_return = True
            while forward_channel_return is True:
                current_time_rounded = round(time.time())
                if current_time_rounded != last_save_time:
                    lxd_interface.set_description(self.instance_name, str(current_time_rounded))
                    last_save_time = current_time_rounded

                if "client_channel" in locals():
                    forward_channel_return = self.forward_channel(client_channel)

            exit_time = round(time.time())
            time.sleep(10)
            while True:
                last_run_time = int(lxd_interface.get_description(self.instance_name))

                if exit_time < last_run_time:
                    break
                elif round(time.time()) > (last_run_time + 15):
                    lxd_interface.destroy_instance(self.instance_name)
                    break

    def forward_channel(self, client_channel) -> bool:
        if self.channel is None:
            return False
        else:
            r, w, e = select.select([client_channel, self.channel], [], [])
            if self.channel in r:
                x = self.channel.recv(1024)
                if len(x) == 0:
                    self.channel.close()
                    return False
                client_channel.send(x)
            if client_channel in r:
                x = client_channel.recv(1024)
                if len(x) == 0:
                    self.channel.close()
                    return False
                self.channel.send(x)
            return True


Handler.check_channel_request = check_channel_request
Handler.check_channel_shell_request = check_channel_shell_request
Handler.check_channel_subsystem_request = check_channel_subsystem_request
Handler.check_auth_none = check_auth_none
Handler.check_auth_password = check_auth_password
Handler.check_auth_publickey = check_auth_publickey
Handler.enable_auth_gssapi = paramiko.server.ServerInterface.enable_auth_gssapi
Handler.get_allowed_auths = paramiko.server.ServerInterface.get_allowed_auths
