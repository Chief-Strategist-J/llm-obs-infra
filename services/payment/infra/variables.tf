/*
ALGORITHM:
1. Declare service_name for generic reuse across service stacks
2. Declare GCP project, region, zone, and services enablement variables
3. Declare IAM least-privilege service account, roles, and scopes variables
4. Declare network topology, CIDRs, ports, and NAT variables
5. Declare instance hardware, OS image, disk, tags, and labels variables
6. Declare compute MIG, autoscaling thresholds, and health check parameters
*/

variable "service_name" {
  type        = string
  description = "Target service name used to automatically prefix resources (e.g. user, auth, payment)"
  default     = "user"
}

variable "gcp_project_id" {
  type        = string
  description = "Google Cloud Project ID where resources will be provisioned"
}

variable "gcp_region" {
  type        = string
  description = "Google Cloud Region for the infrastructure"
  default     = "us-central1"
}

variable "gcp_zone" {
  type        = string
  description = "Google Cloud Zone for compute resources"
  default     = "us-central1-a"
}

variable "gcp_services" {
  type        = list(string)
  description = "Required Google Cloud APIs to enable for the infrastructure"
  default = [
    "compute.googleapis.com",
    "iam.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com"
  ]
}

variable "service_account_id" {
  type        = string
  description = "Optional override for Compute Service Account ID; derived from service_name if empty"
  default     = ""
}

variable "service_account_roles" {
  type        = list(string)
  description = "Least privilege IAM roles granted to the compute service account"
  default = [
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/monitoring.viewer"
  ]
}

variable "service_account_scopes" {
  type        = list(string)
  description = "OAuth scopes attached to instances"
  default = [
    "https://www.googleapis.com/auth/logging.write",
    "https://www.googleapis.com/auth/monitoring.write"
  ]
}

variable "vpc_name" {
  type        = string
  description = "Optional override for custom VPC network name; derived from service_name if empty"
  default     = ""
}

variable "subnet_name" {
  type        = string
  description = "Optional override for custom subnet name; derived from service_name if empty"
  default     = ""
}

variable "subnet_cidr" {
  type        = string
  description = "Subnet CIDR range"
  default     = "10.0.40.0/24"
}

variable "enable_nat" {
  type        = bool
  description = "Deploy Cloud Router and NAT for outbound internet connectivity"
  default     = true
}

variable "allowed_source_ranges" {
  type        = list(string)
  description = "CIDR blocks allowed for service ingress traffic"
  default     = ["0.0.0.0/0"]
}

variable "ssh_allowed_source_ranges" {
  type        = list(string)
  description = "CIDR blocks allowed for SSH access (port 22)"
  default     = ["0.0.0.0/0"]
}

variable "service_ports" {
  type        = list(string)
  description = "Service ports exposed: DB, Redis, Kafka, OTel, Registry"
  default     = ["5435", "6382", "9095", "4323", "4324", "31429"]
}

variable "network_tags" {
  type        = list(string)
  description = "Network tags applied to nodes; derived from service_name if empty"
  default     = []
}

variable "machine_type" {
  type        = string
  description = "GCP Compute Engine machine type"
  default     = "e2-standard-4"
}

variable "image_family" {
  type        = string
  description = "OS Image family"
  default     = "ubuntu-2204-lts"
}

variable "image_project" {
  type        = string
  description = "GCP Image project"
  default     = "ubuntu-os-cloud"
}

variable "disk_size_gb" {
  type        = number
  description = "Boot disk size in GB"
  default     = 50
}

variable "disk_type" {
  type        = string
  description = "Boot disk type (pd-standard, pd-balanced, pd-ssd)"
  default     = "pd-ssd"
}

variable "assign_public_ip" {
  type        = bool
  description = "Whether to assign public IPs to instances"
  default     = true
}

variable "instance_labels" {
  type        = map(string)
  description = "Key-value labels for instance tracking and cost allocation"
  default = {
    environment = "development"
    managed_by  = "terraform"
  }
}

variable "custom_startup_script" {
  type        = string
  description = "Optional override for startup script; uses default modular script if empty"
  default     = ""
}

variable "enable_oslogin" {
  type        = bool
  description = "Enforce OS Login for secure SSH access"
  default     = true
}

variable "instance_name" {
  type        = string
  description = "Optional override for base instance name; derived from service_name if empty"
  default     = ""
}

variable "target_size" {
  type        = number
  description = "Initial target number of instances in the group"
  default     = 1
}

variable "min_replicas" {
  type        = number
  description = "Minimum number of instances during autoscaling"
  default     = 1
}

variable "max_replicas" {
  type        = number
  description = "Maximum number of instances during autoscaling"
  default     = 3
}

variable "cooldown_period_sec" {
  type        = number
  description = "Autoscaler cooldown period in seconds"
  default     = 60
}

variable "target_cpu_utilization" {
  type        = number
  description = "Target CPU utilization percentage for horizontal scaling (0.1 to 0.9)"
  default     = 0.70
}

variable "health_check_port" {
  type        = number
  description = "Port used for compute node health check probes"
  default     = 22
}

variable "health_check_interval_sec" {
  type        = number
  description = "Health check probe interval in seconds"
  default     = 15
}

variable "health_check_timeout_sec" {
  type        = number
  description = "Health check timeout in seconds"
  default     = 5
}

variable "healthy_threshold" {
  type        = number
  description = "Number of consecutive successes to mark healthy"
  default     = 2
}

variable "unhealthy_threshold" {
  type        = number
  description = "Number of consecutive failures to mark unhealthy"
  default     = 3
}

variable "health_check_initial_delay_sec" {
  type        = number
  description = "Autohealing initial delay in seconds"
  default     = 300
}

variable "named_ports" {
  type = list(object({
    name = string
    port = number
  }))
  description = "Named ports for the instance group"
  default = [
    { name = "database", port = 5435 },
    { name = "redis", port = 6382 },
    { name = "kafka", port = 9095 },
    { name = "otel", port = 4323 },
    { name = "registry", port = 31429 }
  ]
}
