from sshim import *
import paramiko
import os


def check_auth_none(self, username):
    return paramiko.AUTH_PARTIALLY_SUCCESSFUL


def check_auth_password(self, username, password):
    if username == os.environ["ssh-username"] and password == os.environ["ssh-password"]:
        return paramiko.AUTH_SUCCESSFUL
    return paramiko.AUTH_FAILED


def check_auth_publickey(self, username, key):
    return paramiko.AUTH_FAILED


def enable_auth_gssapi(self):
    return paramiko.AUTH_FAILED


Handler.check_auth_none = check_auth_none
Handler.check_auth_password = check_auth_password
Handler.check_auth_publickey = check_auth_publickey
Handler.enable_auth_gssapi = enable_auth_gssapi

