/*
ALGORITHM:
1. Export VPC network ID, name, and self-link
2. Export Subnetwork ID, name, self-link, and CIDR block
*/

output "network_id" {
  value       = google_compute_network.user_vpc.id
  description = "ID of the created VPC network"
}

output "network_name" {
  value       = google_compute_network.user_vpc.name
  description = "Name of the created VPC network"
}

output "network_self_link" {
  value       = google_compute_network.user_vpc.self_link
  description = "Self link URI of the created VPC network"
}

output "subnetwork_id" {
  value       = google_compute_subnetwork.user_subnet.id
  description = "ID of the created subnetwork"
}

output "subnetwork_name" {
  value       = google_compute_subnetwork.user_subnet.name
  description = "Name of the created subnetwork"
}

output "subnetwork_self_link" {
  value       = google_compute_subnetwork.user_subnet.self_link
  description = "Self link URI of the created subnetwork"
}

output "subnetwork_cidr" {
  value       = google_compute_subnetwork.user_subnet.ip_cidr_range
  description = "CIDR range allocated to the subnetwork"
}
