output "vpc_name" {
  value       = google_compute_network.storage_vpc.name
  description = "Provisioned GCP VPC Network Name"
}

output "subnet_name" {
  value       = google_compute_subnetwork.storage_subnet.name
  description = "Provisioned GCP Subnet Name"
}

output "storage_node_public_ip" {
  value       = google_compute_address.storage_ip.address
  description = "External Static IP address of the GCP Storage Infrastructure Node"
}

output "storage_node_private_ip" {
  value       = google_compute_instance.storage_node.network_interface[0].network_ip
  description = "Internal Private IP address of the GCP Storage Infrastructure Node"
}

output "ssh_connection_command" {
  value       = "gcloud compute ssh ${google_compute_instance.storage_node.name} --zone=${var.gcp_zone} --project=${var.gcp_project_id}"
  description = "gcloud SSH command to access the deployment node"
}

output "service_endpoints" {
  value = {
    database         = "${google_compute_address.storage_ip.address}:5436"
    redis_ledger     = "${google_compute_address.storage_ip.address}:6383"
    kafka_broker     = "${google_compute_address.storage_ip.address}:9096"
    otel_collector   = "http://${google_compute_address.storage_ip.address}:4325"
    service_registry = "http://${google_compute_address.storage_ip.address}:31430"
  }
  description = "Public connection endpoints for all 5 Storage services"
}
