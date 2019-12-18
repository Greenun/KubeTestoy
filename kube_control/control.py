from kubernetes import client, config
import hashlib
import os


MAIN_INGRESS = "main-ingress"
REGISTRY_PREFIX = os.environ.get("REGISTRY_HOST", "asia.gcr.io/k8stestinfra/")
config.load_kube_config()


def describe_deployment(name: str, namespace: str = 'default'):
    beta_v1 = client.AppsV1beta1Api()
    # res = beta_v1.list_namespaced_deployment(namespace='default')
    res = beta_v1.read_namespaced_deployment(name, namespace)
    # print(res)
    return res


def describe_ingress(name: str, namespace: str = "default", api_instance = None):
    ext_v1_beta = client.ExtensionsV1beta1Api() if not api_instance else api_instance
    resp = ext_v1_beta.read_namespaced_ingress(name=name, namespace=namespace)
    # resp = ext_v1_beta.list_ingress_for_all_namespaces()
    return resp


def create_deployment(project_name: str, images: list, ports: dict = {}, envs: dict = {}):
    # parameter : project_name:str, images:list, ports:dict {image_name: port_list}, envs:dict (image_name: env)
    # label name --> project name + etc..
    # readinessProbe .. tcp or http
    # envs --> image_name : env --> env: list of dict ({name: xxx, value: xxx})
    containers = list()
    for image in images:
        name = image.split(":")[0]
        tag = image.split(":")[1]
        container_ports = [client.V1ContainerPort(p) for p in ports[image]] if ports and ports.get(image) else None
        print(envs)
        container_envs = [client.V1EnvVar(name=e.get("name"), value=e.get("value")) for e in envs.get(image)]\
            if envs.get(image) else None
        image = REGISTRY_PREFIX + image

        containers.append(client.V1Container(
            name=name,
            image=image,
            # ports=container_ports,
            env=container_envs,
            readiness_probe=client.V1Probe(
                initial_delay_seconds=10,
                period_seconds=15,
                tcp_socket=client.V1TCPSocketAction(port=container_ports[0].container_port)
            ),
            image_pull_policy="Always" if tag == "latest" else "IfNotPresent"
        ))
    # print(containers)

    project_hash = hashlib.sha256(project_name.encode()).hexdigest()[:16]
    labels = {"identifier": project_hash}
    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels=labels),
        spec=client.V1PodSpec(containers=containers)
    )

    spec = client.V1DeploymentSpec(
        replicas=1, # default
        template=template,
        selector={'matchLabels': labels},
    )

    deployment = client.V1Deployment(
        api_version="apps/v1",
        kind="Deployment",
        metadata=client.V1ObjectMeta(name=project_hash+"-deployment"),
        spec=spec
    )

    v1 = client.AppsV1Api()
    resp = v1.create_namespaced_deployment(
        body=deployment,
        namespace="default"
    )
    # print(resp)
    return resp


def create_service(project_name: str, service_ports: list, service_type: str = None, namespace: str = "default"):
    default_expose = 30000
    project_hash = hashlib.sha256(project_name.encode()).hexdigest()[:16]
    spec_ports = [client.V1ServicePort(port=default_expose + idx, target_port=p) for idx, p in enumerate(service_ports)]

    service_spec = client.V1ServiceSpec(
        selector={"identifier": project_hash},
        type="NodePort" if not service_type else service_type,
        ports=spec_ports
    )
    service = client.V1Service(
        api_version="v1",
        metadata=client.V1ObjectMeta(name="p"+project_hash+"-service"),
        spec=service_spec
    )

    v1 = client.CoreV1Api()
    resp = v1.create_namespaced_service(
        namespace=namespace,
        body=service
    )
    # print(resp)
    return resp


def add_ingress_rules(name: str, project_name: str, service_port: int,  namespace: str = "default"):
    # update ingress path rules
    project_hash = hashlib.sha256(project_name.encode()).hexdigest()[:16]
    service_name = f'p{project_hash}-service'

    ext_v1_beta = client.ExtensionsV1beta1Api()
    prev_ingress = describe_ingress(name=name)
    path_rule = client.ExtensionsV1beta1HTTPIngressPath(
        backend=client.ExtensionsV1beta1IngressBackend(
            service_name=service_name,
            service_port=service_port
        ),
        path=f'/{project_hash}/(.*)'
    )
    prev_ingress.spec.rules[0].http.paths.append(path_rule)

    resp = ext_v1_beta.replace_namespaced_ingress(name=name, namespace=namespace, body=prev_ingress)
    # print(resp)
    return resp


def remove_ingress_rules(name: str, project_name: str, namespace: str = "default"):
    # remove ingress path rules
    project_hash = hashlib.sha256(project_name.encode()).hexdigest()[:16]
    service_name = f'p{project_hash}-service'

    ext_v1_beta = client.ExtensionsV1beta1Api()
    prev_ingress = describe_ingress(name=name)

    path_rules = prev_ingress.spec.rules[0].http.paths

    target_idx = -1
    for idx, path_rule in enumerate(path_rules):
        if path_rule.backend.service_name == service_name:
            target_idx = idx
    if target_idx == -1:
        return {"status": "failed", "msg": "Service Not Found"}

    prev_ingress.spec.rules[0].http.paths.pop(target_idx)

    resp = ext_v1_beta.replace_namespaced_ingress(name=name, namespace=namespace, body=prev_ingress)
    # print(resp)
    return resp


def delete_service(project_name: str, namespace: str = "default"):
    project_hash = hashlib.sha256(project_name.encode()).hexdigest()[:16]
    v1 = client.CoreV1Api()
    resp = v1.delete_namespaced_service(
        name=f'p{project_hash}-service',
        namespace=namespace
    )
    # print(resp)
    return resp


def delete_deployment(project_name: str, namespace: str = "default"):
    project_hash = hashlib.sha256(project_name.encode()).hexdigest()[:16]
    v1 = client.AppsV1Api()
    resp = v1.delete_namespaced_deployment(
        name=f'{project_hash}-deployment',
        namespace=namespace
    )
    # print(resp)
    return resp


def update_deployment(project_name: str, images: list, ports: dict = {}, envs: dict = {}, namespace: str = "default"):
    # update deployment image tag
    # image add / replace
    project_hash = hashlib.sha256(project_name.encode()).hexdigest()[:16]
    deployment_name = f"{project_hash}-deployment"
    prev_deployment = describe_deployment(name=deployment_name)

    prev_containers = prev_deployment.spec.template.spec.containers
    # print(prev_containers)
    prev_images = list()
    for prev_container in prev_containers:
        prev_images.append(prev_container.image.replace(REGISTRY_PREFIX, ""))
    prev_image_names = [p.split(":")[0] for p in prev_images]

    add_patch, replace_patch = list(), list()
    for idx, image in enumerate(images):
        # different name
        if image.split(":")[0] not in prev_image_names:
            add_patch.append(image)
            continue
        # different tag or latest
        for i, prev_image in enumerate(prev_images):
            if prev_image.split(":")[0] == image.split(":")[0]:
                replace_patch.append((i, image))
    v1 = client.AppsV1Api()

    for add_p in add_patch:
        new_container = client.V1Container(
            name=add_p.split(":")[0],
            image=REGISTRY_PREFIX+add_p,
            readiness_probe=client.V1Probe(
                initial_delay_seconds=10,
                period_seconds=20,
                tcp_socket=client.V1TCPSocketAction(port=client.V1ContainerPort(8080))
            )
        )
        # prev_deployment.spec.template.spec.containers.append(new_container)

    for replace_p in replace_patch:
        if replace_p[1].split(':')[1] == 'latest':
            prev_is = prev_deployment.spec.template.spec.containers[replace_p[0]].readiness_probe.initial_delay_seconds
            now_is = 10 if prev_is > 10 else 15
            prev_deployment.spec.template.spec.containers[replace_p[0]].readiness_probe.initial_delay_seconds = now_is
        else:
            prev_deployment.spec.template.spec.containers[replace_p[0]].image = REGISTRY_PREFIX + replace_p[1]
    # print(prev_deployment)
    resp = v1.patch_namespaced_deployment(
        name=deployment_name,
        namespace=namespace,
        body=prev_deployment
    )
    return resp


def delete_sequence(project_name: str, namespace: str = "default"):
    ingress_resp = remove_ingress_rules(MAIN_INGRESS, project_name)
    service_resp = delete_service(project_name)
    deployment_resp = delete_deployment(project_name)

    return deployment_resp


def create_sequence(project_name: str, images: list, ports: dict = {}, envs: dict = {}):
    deployment_resp = create_deployment(project_name, images, ports, envs)
    service_resp = create_service(project_name, ports.get(images[0]))  # only one exposure image
    ingress_resp = add_ingress_rules(MAIN_INGRESS, project_name, 30000)  # default --> 30000

    return deployment_resp


if __name__ == '__main__':
    # create_deployment('test-project', ["web-test:latest"], {"web-test:latest": [8080]},
    #                   {"web-test:latest": [{"name": "TEST", "value": "TEST_VALUE"}]})
    # describe_deployment(name="hello-kubernetes-deployment")
    # create_service(project_name="test-project", service_ports=[8080])

    # delete_deployment("test-project")
    # remove_ingress_rules(MAIN_INGRESS, "test-project")
    # add_ingress_rules("my-ingress", "test-project", 30000)
    # update_deployment("test-project", ['web-test:latest'], {})
    # delete_sequence('test-project')
    # create_sequence('test-project', ["web-test:latest"],
    #                 {"web-test:latest": [8080]},
    #                 {"web-test:latest": [{"name": "TEST", "value": "TEST_VALUE"}]})
    # create_sequence('test-project-2', ["web-test:latest"],
    #                 {"web-test:latest": [8080]},
    #                 {"web-test:latest": [{"name": "TEST_2", "value": "TEST_VALUE_2"}]})
    resp = describe_ingress(MAIN_INGRESS)
    # print(resp)
    pass

