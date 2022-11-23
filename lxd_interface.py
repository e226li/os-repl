import pylxd

lxd_client = pylxd.client.Client()


def create_instance(container_name: str):
    config = {'name': container_name, 'source':
    {'type': 'image', "mode": "pull", "server": "https://cloud-images.ubuntu.com/daily", "protocol": "simplestreams",
     'alias': 'lts/amd64'}, 'security.nesting': 'true'}

    instance = lxd_client.instances.create(config, wait=True)
    instance.start()

    return True


def destroy_instance(container_name: str):
    instance = lxd_client.instances.get(container_name)
    instance.stop(wait=True)
    instance.delete(wait=True)

    return True
