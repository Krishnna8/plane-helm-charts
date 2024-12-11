import kopf
import kubernetes.client
from kubernetes.client.rest import ApiException

def create_deployment(name, namespace, replicas, image, resources, config, component):
    """Creates a Kubernetes Deployment specification for Plane CE components."""
    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": f"{name}-{component}",
            "namespace": namespace,
        },
        "spec": {
            "replicas": replicas,
            "selector": {
                "matchLabels": {
                    "app": f"{name}-{component}"
                }
            },
            "template": {
                "metadata": {
                    "labels": {
                        "app": f"{name}-{component}"
                    }
                },
                "spec": {
                    "containers": [
                        {
                            "name": component,
                            "image": image,
                            "resources": resources,
                            "env": [
                                {"name": key, "value": str(value)} for key, value in config.items()
                            ]
                        }
                    ]
                }
            }
        }
    }

def create_service(name, namespace, component, ports):
    """Creates a Kubernetes Service specification for Plane CE components."""
    return {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": f"{name}-{component}",
            "namespace": namespace,
        },
        "spec": {
            "selector": {
                "app": f"{name}-{component}"
            },
            "ports": ports
        }
    }

def create_configmap(name, namespace, config):
    """Creates a ConfigMap for Plane CE."""
    return {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {
            "name": name,
            "namespace": namespace
        },
        "data": config
    }

@kopf.on.create('example.com', 'v1', 'planes')
def create_fn(spec, name, namespace, **kwargs):
    """Handles the creation of a Plane custom resource."""
    components = {
        "web": {"replicas": 2, "image": spec.get('webImage', 'plane-ce-web:latest')},
        "space": {"replicas": 1, "image": spec.get('spaceImage', 'plane-ce-space:latest')},
        "live": {"replicas": 1, "image": spec.get('liveImage', 'plane-ce-live:latest')},
        "api": {"replicas": 2, "image": spec.get('apiImage', 'plane-ce-api:latest')},
        "worker": {"replicas": 2, "image": spec.get('workerImage', 'plane-ce-worker:latest')},
        "beat-worker": {"replicas": 1, "image": spec.get('beatWorkerImage', 'plane-ce-beat-worker:latest')}
    }

    resources = spec.get('resources', {})
    config = spec.get('config', {})

    api_apps = kubernetes.client.AppsV1Api()
    api_core = kubernetes.client.CoreV1Api()

    for component, details in components.items():
        deployment = create_deployment(name, namespace, details['replicas'], details['image'], resources, config, component)
        service = create_service(name, namespace, component, ports=[{"protocol": "TCP", "port": 80, "targetPort": 8080}])

        try:
            # Create the Deployment
            api_apps.create_namespaced_deployment(namespace=namespace, body=deployment)
            kopf.info(f"Deployment {name}-{component} created.")

            # Create the Service
            api_core.create_namespaced_service(namespace=namespace, body=service)
            kopf.info(f"Service {name}-{component} created.")

        except ApiException as e:
            raise kopf.TemporaryError(f"Error creating {component} resources: {e}", delay=30)

    # Create the ConfigMap
    configmap = create_configmap(f"{name}-config", namespace, config)
    try:
        api_core.create_namespaced_config_map(namespace=namespace, body=configmap)
        kopf.info(f"ConfigMap {name}-config created.")
    except ApiException as e:
        raise kopf.TemporaryError(f"Error creating ConfigMap: {e}", delay=30)

@kopf.on.update('example.com', 'v1', 'planes')
def update_fn(spec, name, namespace, **kwargs):
    """Handles updates to a Plane custom resource."""
    components = {
        "web": {"replicas": 2, "image": spec.get('webImage', 'plane-ce-web:latest')},
        "space": {"replicas": 1, "image": spec.get('spaceImage', 'plane-ce-space:latest')},
        "live": {"replicas": 1, "image": spec.get('liveImage', 'plane-ce-live:latest')},
        "api": {"replicas": 2, "image": spec.get('apiImage', 'plane-ce-api:latest')},
        "worker": {"replicas": 2, "image": spec.get('workerImage', 'plane-ce-worker:latest')},
        "beat-worker": {"replicas": 1, "image": spec.get('beatWorkerImage', 'plane-ce-beat-worker:latest')}
    }

    resources = spec.get('resources', {})
    config = spec.get('config', {})

    api_apps = kubernetes.client.AppsV1Api()
    api_core = kubernetes.client.CoreV1Api()

    for component, details in components.items():
        deployment = create_deployment(name, namespace, details['replicas'], details['image'], resources, config, component)

        try:
            # Update the Deployment
            api_apps.replace_namespaced_deployment(name=f"{name}-{component}", namespace=namespace, body=deployment)
            kopf.info(f"Deployment {name}-{component} updated.")
        except ApiException as e:
            raise kopf.TemporaryError(f"Error updating {component} resources: {e}", delay=30)

    # Update the ConfigMap
    configmap = create_configmap(f"{name}-config", namespace, config)
    try:
        api_core.replace_namespaced_config_map(name=f"{name}-config", namespace=namespace, body=configmap)
        kopf.info(f"ConfigMap {name}-config updated.")
    except ApiException as e:
        raise kopf.TemporaryError(f"Error updating ConfigMap: {e}", delay=30)

@kopf.on.delete('example.com', 'v1', 'planes')
def delete_fn(name, namespace, **kwargs):
    """Handles deletion of a Plane custom resource."""
    components = ["web", "space", "live", "api", "worker", "beat-worker"]

    api_apps = kubernetes.client.AppsV1Api()
    api_core = kubernetes.client.CoreV1Api()

    for component in components:
        try:
            # Delete the Deployment
            api_apps.delete_namespaced_deployment(name=f"{name}-{component}", namespace=namespace)
            kopf.info(f"Deployment {name}-{component} deleted.")

            # Delete the Service
            api_core.delete_namespaced_service(name=f"{name}-{component}", namespace=namespace)
            kopf.info(f"Service {name}-{component} deleted.")

        except ApiException as e:
            kopf.warning(f"Error deleting {component} resources: {e}")

    # Delete the ConfigMap
    try:
        api_core.delete_namespaced_config_map(name=f"{name}-config", namespace=namespace)
        kopf.info(f"ConfigMap {name}-config deleted.")
    except ApiException as e:
        kopf.warning(f"Error deleting ConfigMap: {e}")
