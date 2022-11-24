from sshim import *
import paramiko
import os
import six
import codecs


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


Script.expect = expect

Handler.check_auth_none = check_auth_none
Handler.check_auth_password = check_auth_password
Handler.check_auth_publickey = check_auth_publickey
Handler.enable_auth_gssapi = paramiko.server.ServerInterface.enable_auth_gssapi
Handler.get_allowed_auths = paramiko.server.ServerInterface.get_allowed_auths