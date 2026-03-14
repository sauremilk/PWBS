{{/*
PWBS Helm Chart Helpers
*/}}

{{- define "pwbs.fullname" -}}
{{- default .Chart.Name .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "pwbs.labels" -}}
app.kubernetes.io/name: {{ include "pwbs.fullname" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end -}}

{{- define "pwbs.selectorLabels" -}}
app.kubernetes.io/name: {{ include "pwbs.fullname" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
