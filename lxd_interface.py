import time
import pylxd
import ipaddress

lxd_client = pylxd.client.Client()


def create_instance(container_name: str, instance_password: str):
    config = {'name': container_name, 'source':
    {'type': 'image', "mode": "pull", "server": "https://cloud-images.ubuntu.com/daily", "protocol": "simplestreams",
     'alias': 'lts/amd64'}, 'config': {'security.nesting': 'true'}}

    instance = lxd_client.instances.create(config, wait=True)
    instance.start(wait=True)
    while type(ipaddress.ip_address(instance.state().network['eth0']['addresses'][0]['address'])) != ipaddress.IPv4Address:
        time.sleep(0.1)

    setup_ssh(container_name, instance_password)

    return instance.state().network['eth0']['addresses'][0]


def destroy_instance(container_name: str):
    instance = lxd_client.instances.get(container_name)
    instance.stop(wait=True)
    instance.delete(wait=True)

    return True


def destroy_all_instances():
    for instance in lxd_client.instances.all():
        instance.stop(wait=True)
        instance.delete(wait=True)

    return True


def execute_command(container_name: str, command: list, stdin_payload=None):
    instance = lxd_client.instances.get(container_name)
    result_tuple = instance.execute(command, stdin_payload=stdin_payload)

    return result_tuple


def setup_ssh(container_name: str, instance_password: str):
    execute_command(container_name,
                    ["sed", "-i", "s/PasswordAuthentication no/PasswordAuthentication yes/", "/etc/ssh/sshd_config"])
    execute_command(container_name,
                    ["sed", "-i", "s/#PermitRootLogin prohibit-password/PermitRootLogin yes/",
                     "/etc/ssh/sshd_config"])
    execute_command(container_name, ["systemctl", "restart", "sshd"])
    execute_command(container_name, ["passwd", "root"], stdin_payload=f"{instance_password}\n{instance_password}")

    return True


def get_networking(container_name: str):
    instance = lxd_client.instances.get(container_name)

    return instance.state().network['eth0']['addresses'][0]


def set_description(container_name: str, new_value: str):
    instance = lxd_client.instances.get(container_name)
    instance.description = new_value
    instance.save()

    return True


def get_description(container_name: str) -> str:
    instance = lxd_client.instances.get(container_name)

    return instance.description
