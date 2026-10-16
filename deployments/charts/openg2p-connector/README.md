# OpenG2P Connector

Helm chart for the OpenG2P Connector Service.

One image runs several roles via container args: `api`, `worker`, `beat`,
optional `consumer`. See the chart `values.yaml` and repo `DEPLOYMENT.md`.

```bash
helm dependency update deployments/charts/openg2p-connector
helm upgrade --install connector deployments/charts/openg2p-connector \
  --namespace <ns> \
  -f values-override.yaml
```
