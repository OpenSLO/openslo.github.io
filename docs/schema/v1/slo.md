# SLO

A Service is a high-level grouping of SLO.
It may be defined before creating SLO to be able to refer to it in SLO's spec.service.
Multiple SLOs can refer to the same Service.

## Examples

=== "Basic"

    ```yaml
    apiVersion: openslo/v1
    kind: SLO
    metadata:
      name: main-page
      displayName: Main page availability
    spec:
      description: Our main page should be available always
      service: web-shop
      indicator:
        metadata:
          name: response-code
          displayName: Response codes of requests to main page
        spec:
          ratioMetric:
            good: # In most cases it is easier to think about timeslices in ratio metrics.
              metricSource:
                type: Any # Here put any service that holds information you need.
                spec: # Fields necessary to query service for the data.
                  query: Any # 'query' is just an example field.
            total:
              metricSource:
                type: Any # Here put any service that holds information you need.
                spec: # Fields necessary to query service for the data.
                  query: Any # 'query' is just an example field.
      timeWindow:
       - duration: 2w
         isRolling: true
      budgetingMethod: RatioTimeslices
      objectives:
        - displayName: Good
          op: gt
          timeSliceWindow: 1m
          target: 0.99
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

{{ generate_object_properties("openslo/v1", "SLO") }}
