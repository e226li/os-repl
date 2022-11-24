import logging
import paramiko
import sshim_patch as sshim
import lxd_interface
import os
import re
import uuid

logging.basicConfig(level='DEBUG')
logger = logging.getLogger()


def connect_handler(script: sshim.Script):
    instance_name = "instance-" + str(uuid.uuid4())
    lxd_interface.create_instance(instance_name)
    with paramiko.ProxyCommand(command_line=f'lxc exec {instance_name} -- /bin/bash') as proxy_command:
        script.writeline(instance_name)
        while True:
            input_command = script.expect(None, echo=True) # TODO: change to false
            proxy_command.send(input_command.encode())
            script.sendall(proxy_command.recv(100))  # TODO: fix
            script.writeline("Sent!")


server = sshim.Server(connect_handler, address='127.0.0.1', port=3022)
try:
    server.run()
except KeyboardInterrupt:
    server.stop()
