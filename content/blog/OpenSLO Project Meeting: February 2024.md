---
title: "OpenSLO Project Meeting: February 2024"
date: 2024-02-21T13:00:00+02:00
draft: false
author: Pawel Rusakiewicz
cover: /images/openslo_logo.svg
---
First community meeting in 2024

## Summary of Meeting

During the meeting, several agenda items were discussed and decisions were made regarding the OpenSLO project.

1. **Source of Truth for OpenSLO manifest**:
   The group decided to use Go structs as the source of truth for the OpenSLO manifest. This decision was made to ensure more control over validation. The plan is to generate JSON Schema/CRDs based on Go structs.

2. **Labels Support**:
   Labels support is to be extended for all objects' metadata, including adding labels to Objective and supporting multiple alert conditions.

3. **Conversion Removal**:
   The decision was made to remove the conversion entirely and extend Oslo documentation on the usage of annotations for vendor-specific conversions. The focus will be on improving the SDK instead of expanding Oslo's responsibilities.

4. **Action Items**:
   Several action items were noted, including documenting new use cases of OpenSLO, reaching out to Grafana regarding an issue, ensuring full Kubernetes compatibility, and considering bringing OpenSLO under CNCF's umbrella.

The next meeting is scheduled for a month later. Precise date TBD.

### Meeting recording
{{< youtube zxRa2sWz0Ag >}}