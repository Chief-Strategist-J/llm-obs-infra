/*
ALGORITHM:
1. Declare project, zone, and instance naming parameters
2. Declare instance template linkage input
3. Declare scaling parameters: min_replicas, max_replicas, cooldown, CPU threshold
4. Declare named ports and health check parameters
*/

variable "project_id" {
  type        = string
  description = "Google Cloud Project ID"
}

variable "zone" {
  type        = string
  description = "GCP availability zone for the Managed Instance Group"
}

variable "base_instance_name" {
  type        = string
  description = "Base instance name prefix for instances in the group"
}

variable "instance_template_self_link" {
  type        = string
  description = "Self link of the instance template from instance layer"
}

variable "target_size" {
  type        = number
  description = "Initial target size of instances in the group"
}

variable "min_replicas" {
  type        = number
  description = "Minimum number of instances for autoscaling"
}

variable "max_replicas" {
  type        = number
  description = "Maximum number of instances for autoscaling"
}

variable "cooldown_period_sec" {
  type        = number
  description = "Autoscaling cooldown period in seconds"
}

variable "target_cpu_utilization" {
  type        = number
  description = "Target CPU utilization percentage threshold for autoscaling (0.1 to 0.9)"
}

variable "named_ports" {
  type = list(object({
    name = string
    port = number
  }))
  description = "Named ports exposed by instances in the group"
  default     = []
}

variable "health_check_port" {
  type        = number
  description = "Port to probe for compute node health checking"
}

variable "health_check_interval_sec" {
  type        = number
  description = "Interval between health checks in seconds"
  default     = 15
}

variable "health_check_timeout_sec" {
  type        = number
  description = "Timeout for health check probe in seconds"
  default     = 5
}

variable "healthy_threshold" {
  type        = number
  description = "Consecutive successes required to mark instance healthy"
  default     = 2
}

variable "unhealthy_threshold" {
  type        = number
  description = "Consecutive failures required to mark instance unhealthy"
  default     = 3
}

variable "health_check_initial_delay_sec" {
  type        = number
  description = "Delay before starting autohealing health checks on new instances"
  default     = 300
}
