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
   Labels support is to be extended for all objects' metadata, including adding labels to Objective.

3. **Oslo Conversion Removal**:
   The decision was made to remove the conversion entirely and extend [oslo](https://github.com/openslo/oslo) documentation on the usage of annotations for vendor-specific conversions. The focus will be on improving the SDK instead of expanding [oslo's](https://github.com/openslo/oslo) responsibilities.

4. **Action Items**:
   Several action items were noted, including documenting new use cases of OpenSLO, ensuring full Kubernetes compatibility, and considering bringing OpenSLO under CNCF's umbrella.

The next meeting is scheduled the next month. Precise date TBD.

### Meeting recording
{{< youtube zxRa2sWz0Ag >}}