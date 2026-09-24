/*
ALGORITHM:
1. Export Instance Group Manager ID, name, and group link
2. Export Autoscaler ID, name, and policy parameters
3. Export Health Check ID
*/

output "instance_group_manager_id" {
  value       = google_compute_instance_group_manager.user_igm.id
  description = "ID of the Managed Instance Group Manager"
}

output "instance_group_manager_name" {
  value       = google_compute_instance_group_manager.user_igm.name
  description = "Name of the Managed Instance Group Manager"
}

output "instance_group" {
  value       = google_compute_instance_group_manager.user_igm.instance_group
  description = "Instance group URI for load balancer backends"
}

output "autoscaler_id" {
  value       = google_compute_autoscaler.user_autoscaler.id
  description = "ID of the Compute Autoscaler"
}

output "autoscaler_name" {
  value       = google_compute_autoscaler.user_autoscaler.name
  description = "Name of the Compute Autoscaler"
}

output "health_check_id" {
  value       = google_compute_health_check.user_health_check.id
  description = "ID of the Compute Health Check"
}

output "min_replicas" {
  value       = var.min_replicas
  description = "Configured minimum number of replicas"
}

output "max_replicas" {
  value       = var.max_replicas
  description = "Configured maximum number of replicas"
}

output "target_cpu_utilization" {
  value       = var.target_cpu_utilization
  description = "Configured CPU utilization threshold for scaling"
}
