# Service

A Service is a high-level grouping of SLO.
It may be defined before creating SLO to be able to refer to it in SLO's spec.service.
Multiple SLOs can refer to the same Service.

## Examples

=== "Basic"

    ```yaml
    apiVersion: openslo/v1
    kind: Service
    metadata:
      labels:
        env:
          - prod
        team:
          - team-a
          - team-b
      name: example-service
    spec:
      description: Example service description
    ```

=== "Annotations"

    ```yaml
    apiVersion: openslo/v1
    kind: Service
    metadata:
      annotations:
        openslo.com/service-folder: ./my/directory
      labels:
        env:
          - dev
        team:
          - team-a
          - team-b
      name: example-service
    spec:
      description: Example service description
    ```

## Properties

{{ generate_object_properties("openslo/v1", "Service") }}
