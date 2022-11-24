import time
import pylxd
import ipaddress

lxd_client = pylxd.client.Client()


def create_instance(container_name: str):
    config = {'name': container_name, 'source':
    {'type': 'image', "mode": "pull", "server": "https://cloud-images.ubuntu.com/daily", "protocol": "simplestreams",
     'alias': 'lts/amd64'}, 'config': {'security.nesting': 'true'}}

    instance = lxd_client.instances.create(config, wait=True)
    instance.start(wait=True)

    while type(ipaddress.ip_address(instance.state().network['eth0']['addresses'][0]['address'])) != ipaddress.IPv4Address:
        time.sleep(0.1)
    return instance.state().network['eth0']['addresses'][0]


def destroy_instance(container_name: str):
    instance = lxd_client.instances.get(container_name)
    instance.stop(wait=True)
    instance.delete(wait=True)

    return True


def execute_command(container_name: str, command: str):
    instance = lxd_client.instances.get(container_name)
    result_tuple = instance.execute([command])

    return result_tuple
