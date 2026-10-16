{{- define "openg2p-connector.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "openg2p-connector.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name (include "openg2p-connector.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "openg2p-connector.labels" -}}
app.kubernetes.io/name: {{ include "openg2p-connector.name" . }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "openg2p-connector.selectorLabels" -}}
app.kubernetes.io/name: {{ include "openg2p-connector.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "openg2p-connector.serviceAccountName" -}}
{{- printf "%s-sa" (include "openg2p-connector.fullname" .) -}}
{{- end -}}

{{- define "openg2p-connector.image" -}}
{{- printf "%s:%s" .Values.image.repository .Values.image.tag -}}
{{- end -}}

{{- define "openg2p-connector.dbName" -}}
{{- tpl .Values.global.connectorDB . -}}
{{- end -}}

{{- define "openg2p-connector.dbUser" -}}
{{- tpl .Values.global.connectorDBUser . -}}
{{- end -}}

{{- define "openg2p-connector.dbSecret" -}}
{{- tpl .Values.global.connectorDBSecret . -}}
{{- end -}}

{{- define "openg2p-connector.dbPasswordKey" -}}
{{- tpl .Values.global.connectorDBUserPasswordKey . -}}
{{- end -}}

{{- define "openg2p-connector.partnerBaseUrl" -}}
{{- printf "http://%s.%s.svc.cluster.local" .Values.global.partnerApiService .Release.Namespace -}}
{{- end -}}

{{- define "openg2p-connector.postgresWaitArgs" -}}
- -c
- >-
  until PGPASSWORD="${CONNECTOR_DB_PASSWORD}" psql -q
  -U "${CONNECTOR_DB_USERNAME}"
  -h "${CONNECTOR_DB_HOSTNAME}"
  -p "${CONNECTOR_DB_PORT:-5432}"
  -d "${CONNECTOR_DB_DBNAME}"
  -c "SELECT 1" >/dev/null 2>&1;
  do echo "waiting for postgres credentials to work..."; sleep 3; done
{{- end -}}

{{- define "openg2p-connector.commonEnv" -}}
- name: CONNECTOR_DB_DRIVER
  value: {{ .Values.commonEnv.CONNECTOR_DB_DRIVER | quote }}
- name: CONNECTOR_DB_HOSTNAME
  value: {{ .Values.global.postgresqlHost | quote }}
- name: CONNECTOR_DB_PORT
  value: {{ .Values.global.postgresqlPort | quote }}
- name: CONNECTOR_DB_USERNAME
  value: {{ include "openg2p-connector.dbUser" . | quote }}
- name: CONNECTOR_DB_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ include "openg2p-connector.dbSecret" . | quote }}
      key: {{ include "openg2p-connector.dbPasswordKey" . | quote }}
- name: CONNECTOR_DB_DBNAME
  value: {{ include "openg2p-connector.dbName" . | quote }}
- name: CONNECTOR_PARTNER_INGEST_BASE_URL
  value: {{ include "openg2p-connector.partnerBaseUrl" . | quote }}
- name: CONNECTOR_CELERY_BROKER_URL
  value: {{ printf "redis://%s:%v/%v" .Values.global.redisHost .Values.global.redisPort .Values.global.redisDb | quote }}
- name: CONNECTOR_CELERY_RESULT_BACKEND
  value: {{ printf "redis://%s:%v/%v" .Values.global.redisHost .Values.global.redisPort .Values.global.redisDb | quote }}
- name: CONNECTOR_LOG_LEVEL
  value: {{ .Values.commonEnv.CONNECTOR_LOG_LEVEL | quote }}
- name: CONNECTOR_STORE_RUN_PAYLOADS
  value: {{ .Values.commonEnv.CONNECTOR_STORE_RUN_PAYLOADS | quote }}
- name: CONNECTOR_STRICT_INCREMENTAL
  value: {{ .Values.commonEnv.CONNECTOR_STRICT_INCREMENTAL | quote }}
- name: CONNECTOR_FULL_SCAN_ON_INCREMENTAL_UNSUPPORTED
  value: {{ .Values.commonEnv.CONNECTOR_FULL_SCAN_ON_INCREMENTAL_UNSUPPORTED | quote }}
- name: CONNECTOR_METRICS_ENABLED
  value: {{ .Values.commonEnv.CONNECTOR_METRICS_ENABLED | quote }}
- name: CONNECTOR_CORS_ORIGINS
  value: {{ .Values.commonEnv.CONNECTOR_CORS_ORIGINS | quote }}
{{- if .Values.global.metadataDsnSecret }}
- name: CONNECTOR_MASTER_DATA_DB_DSN
  valueFrom:
    secretKeyRef:
      name: {{ .Values.global.metadataDsnSecret | quote }}
      key: {{ .Values.global.masterDataDsnKey | quote }}
- name: CONNECTOR_REGISTRY_DB_DSN
  valueFrom:
    secretKeyRef:
      name: {{ .Values.global.metadataDsnSecret | quote }}
      key: {{ .Values.global.registryDsnKey | quote }}
{{- end }}
{{- end -}}
