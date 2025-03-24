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

### apiVersion

Type: `string`

Rules:

- must be equal to `openslo/v1`

### kind

Type: `string`

Rules:

- must be equal to `Service`

### metadata

#### metadata.name

Type: `string`

| Rules                                                                         | Details | Examples |
| ----------------------------------------------------------------------------- | | |
| length must be between 1 and 63                                               | | |
| string must match regular expression: `^[a-z0-9]([-a-z0-9]*[a-z0-9])?$`       | an RFC-1123 compliant label name must consist of lower case alphanumeric characters or '-', and must start and end with an alphanumeric character | my-name<br>123-abc |

Rules:

- length must be between 1 and 63
- string must match regular expression: `^[a-z0-9]([-a-z0-9]*[a-z0-9])?$`
  
    an RFC-1123 compliant label name must consist of lower case 
    alphanumeric characters or '-', and must start and end with an alphanumeric character

    Examples:

    ```
    my-name
    123-abc
    ```

#### metadata.displayName

Type: `string`

Rules:

- length must be less than or equal to 63

#### metadata.labels

Type: `map[string][]string`

Examples:

#### metadata.annotations

Type: `map[string]string`

Examples:

```yaml
annotations:
  openslo.com/service-folder: ./my/directory
```

### spec

#### spec.description

Type: `string`

Rules:

- length must be less than or equal to 1050
