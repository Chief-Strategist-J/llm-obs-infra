variable "gcp_project_id" {
  type        = string
  description = "Google Cloud Project ID"
}

variable "gcp_region" {
  type        = string
  description = "GCP region for deployment"
  default     = "us-central1"
}

variable "gcp_zone" {
  type        = string
  description = "GCP availability zone"
  default     = "us-central1-a"
}

variable "vpc_name" {
  type        = string
  description = "Custom VPC network name for Storage stack"
  default     = "llmobs-storage-vpc"
}

variable "subnet_cidr" {
  type        = string
  description = "Subnet CIDR range"
  default     = "10.0.50.0/24"
}

variable "instance_name" {
  type        = string
  description = "GCP Compute Engine instance name"
  default     = "llmobs-storage-node"
}

variable "machine_type" {
  type        = string
  description = "GCP Compute Engine machine type"
  default     = "e2-standard-4"
}

variable "allowed_source_ranges" {
  type        = list(string)
  description = "CIDR blocks allowed for ingress traffic"
  default     = ["0.0.0.0/0"]
}
