# Test

A Service is a high-level grouping of SLO.
It may be defined before creating SLO to be able to refer to it in SLO's spec.service.
Multiple SLOs can refer to the same Service.

## Examples

=== "Basic"

    ```yaml
    apiVersion: openslo/v1
    kind: Service
    metadata:
      name: example-service
      displayName: Example Service
    spec:
      description: Example service description
    ```

=== "Full"

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
      displayName: Example Service
    spec:
      description: Example service description
    ```

## Properties

### [`metadata`](../v1.md#metadata)

??? property "<span class='property-type-badge'>string</string></span> <span class='property-status-badge'>required</span>"

    *Some documentation goes here.*

    ---

    **Validation Rules**

    | Rule | Details | Examples |
    | :--- | :------ | :------- |
    | Length | 1-50 chars | `ex-1` |
