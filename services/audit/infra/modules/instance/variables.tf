/*
ALGORITHM:
1. Declare project, regional, and GCP services enablement inputs
2. Declare dedicated Service Account parameters and least-privilege IAM roles/scopes
3. Declare VM hardware inputs: machine type, disk size/type, OS image family/project
4. Declare network binding, public IP toggle, network tags, labels, and startup script
*/

variable "project_id" {
  type        = string
  description = "Google Cloud Project ID"
}

variable "region" {
  type        = string
  description = "GCP region"
}

variable "gcp_services" {
  type        = list(string)
  description = "List of required GCP services / APIs to enable"
}

variable "service_account_id" {
  type        = string
  description = "ID of the dedicated service account for least-privilege access"
}

variable "service_account_display_name" {
  type        = string
  description = "Display name for the dedicated service account"
}

variable "service_account_roles" {
  type        = list(string)
  description = "List of IAM roles to grant to the service account (least-privilege)"
}

variable "service_account_scopes" {
  type        = list(string)
  description = "OAuth scopes granted to the instance template service account"
}

variable "template_name_prefix" {
  type        = string
  description = "Prefix for the instance template name"
}

variable "machine_type" {
  type        = string
  description = "GCP Compute Engine machine type (e.g. e2-standard-4)"
}

variable "image_family" {
  type        = string
  description = "OS Image family (e.g. ubuntu-2204-lts)"
}

variable "image_project" {
  type        = string
  description = "GCP Image project (e.g. ubuntu-os-cloud)"
}

variable "disk_size_gb" {
  type        = number
  description = "Boot disk size in Gigabytes"
}

variable "disk_type" {
  type        = string
  description = "Boot disk type (pd-standard, pd-balanced, or pd-ssd)"
}

variable "network_id" {
  type        = string
  description = "VPC network ID or self link from network layer"
}

variable "subnetwork_id" {
  type        = string
  description = "Subnetwork ID or self link from network layer"
}

variable "assign_public_ip" {
  type        = bool
  description = "Whether instances created from this template should receive external public IP addresses"
}

variable "tags" {
  type        = list(string)
  description = "Network tags applied to instances created from this template"
}

variable "labels" {
  type        = map(string)
  description = "Key-value labels applied to instances created from this template"
}

variable "startup_script" {
  type        = string
  description = "Custom startup script string; if empty, uses default startup.sh"
  default     = ""
}

variable "enable_oslogin" {
  type        = bool
  description = "Whether to enforce Google Cloud OS Login for SSH security"
  default     = true
}
