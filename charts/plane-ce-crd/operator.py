import kopf
import kubernetes.client
from kubernetes.client.rest import ApiException

def create_deployment(name, namespace, replicas, image, resources, config):
    """Creates a Kubernetes Deployment specification for Plane CE."""
    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": name,
            "namespace": namespace,
        },
        "spec": {
            "replicas": replicas,
            "selector": {
                "matchLabels": {
                    "app": name
                }
            },
            "template": {
                "metadata": {
                    "labels": {
                        "app": name
                    }
                },
                "spec": {
                    "containers": [
                        {
                            "name": "plane-ce",
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

def create_service(name, namespace):
    """Creates a Kubernetes Service specification for Plane CE."""
    return {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": name,
            "namespace": namespace,
        },
        "spec": {
            "selector": {
                "app": name
            },
            "ports": [
                {
                    "protocol": "TCP",
                    "port": 80,
                    "targetPort": 8080
                }
            ]
        }
    }

@kopf.on.create('plane.co', 'v1', 'PlaneCE')
def create_fn(spec, name, namespace, **kwargs):
    """Handles the creation of a Plane custom resource."""
    replicas = spec.get('replicas', 1)
    image = spec.get('image', 'plane-ce:latest')
    resources = spec.get('resources', {})
    config = spec.get('config', {})

    deployment = create_deployment(name, namespace, replicas, image, resources, config)
    service = create_service(name, namespace)

    api_apps = kubernetes.client.AppsV1Api()
    api_core = kubernetes.client.CoreV1Api()

    try:
        # Create the Deployment
        api_apps.create_namespaced_deployment(namespace=namespace, body=deployment)
        kopf.info(f"Deployment {name} created.")

        # Create the Service
        api_core.create_namespaced_service(namespace=namespace, body=service)
        kopf.info(f"Service {name} created.")

    except ApiException as e:
        raise kopf.TemporaryError(f"Error creating resources: {e}", delay=30)

@kopf.on.update('plane.co', 'v1', 'PlaneCE')
def update_fn(spec, name, namespace, **kwargs):
    """Handles updates to a Plane custom resource."""
    replicas = spec.get('replicas', 1)
    image = spec.get('image', 'plane-ce:latest')
    resources = spec.get('resources', {})
    config = spec.get('config', {})

    deployment = create_deployment(name, namespace, replicas, image, resources, config)

    api_apps = kubernetes.client.AppsV1Api()

    try:
        # Update the Deployment
        api_apps.replace_namespaced_deployment(name=name, namespace=namespace, body=deployment)
        kopf.info(f"Deployment {name} updated.")

    except ApiException as e:
        raise kopf.TemporaryError(f"Error updating deployment: {e}", delay=30)

@kopf.on.delete('plane.co', 'v1', 'PlaneCE')
def delete_fn(name, namespace, **kwargs):
    """Handles deletion of a Plane custom resource."""
    api_apps = kubernetes.client.AppsV1Api()
    api_core = kubernetes.client.CoreV1Api()

    try:
        # Delete the Deployment
        api_apps.delete_namespaced_deployment(name=name, namespace=namespace)
        kopf.info(f"Deployment {name} deleted.")

        # Delete the Service
        api_core.delete_namespaced_service(name=name, namespace=namespace)
        kopf.info(f"Service {name} deleted.")

    except ApiException as e:
        kopf.warning(f"Error deleting resources: {e}")