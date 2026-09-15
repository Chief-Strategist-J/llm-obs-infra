output "vpc_name" {
  value       = google_compute_network.auth_vpc.name
  description = "Provisioned GCP VPC Network Name"
}

output "subnet_name" {
  value       = google_compute_subnetwork.auth_subnet.name
  description = "Provisioned GCP Subnet Name"
}

output "auth_node_public_ip" {
  value       = google_compute_address.auth_ip.address
  description = "External Static IP address of the GCP Auth Infrastructure Node"
}

output "auth_node_private_ip" {
  value       = google_compute_instance.auth_node.network_interface[0].network_ip
  description = "Internal Private IP address of the GCP Auth Infrastructure Node"
}

output "ssh_connection_command" {
  value       = "gcloud compute ssh ${google_compute_instance.auth_node.name} --zone=${var.gcp_zone} --project=${var.gcp_project_id}"
  description = "gcloud SSH command to access the deployment node"
}

output "service_endpoints" {
  value = {
    database         = "${google_compute_address.auth_ip.address}:5432"
    redis_ledger     = "${google_compute_address.auth_ip.address}:6379"
    kafka_broker     = "${google_compute_address.auth_ip.address}:9092"
    otel_collector   = "http://${google_compute_address.auth_ip.address}:4318"
    service_registry = "http://${google_compute_address.auth_ip.address}:31426"
  }
  description = "Public connection endpoints for all 5 Auth services"
}
