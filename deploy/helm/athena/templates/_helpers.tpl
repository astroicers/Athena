{{- define "athena.fullname" -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "athena.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{ include "athena.selectorLabels" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "athena.selectorLabels" -}}
app.kubernetes.io/name: athena
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
