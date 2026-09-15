output "vpc_name" {
  value       = google_compute_network.payment_vpc.name
  description = "Provisioned GCP VPC Network Name"
}

output "subnet_name" {
  value       = google_compute_subnetwork.payment_subnet.name
  description = "Provisioned GCP Subnet Name"
}

output "payment_node_public_ip" {
  value       = google_compute_address.payment_ip.address
  description = "External Static IP address of the GCP Payment Infrastructure Node"
}

output "payment_node_private_ip" {
  value       = google_compute_instance.payment_node.network_interface[0].network_ip
  description = "Internal Private IP address of the GCP Payment Infrastructure Node"
}

output "ssh_connection_command" {
  value       = "gcloud compute ssh ${google_compute_instance.payment_node.name} --zone=${var.gcp_zone} --project=${var.gcp_project_id}"
  description = "gcloud SSH command to access the deployment node"
}

output "service_endpoints" {
  value = {
    database         = "${google_compute_address.payment_ip.address}:5433"
    redis_ledger     = "${google_compute_address.payment_ip.address}:6380"
    kafka_broker     = "${google_compute_address.payment_ip.address}:9093"
    otel_collector   = "http://${google_compute_address.payment_ip.address}:4319"
    service_registry = "http://${google_compute_address.payment_ip.address}:31427"
  }
  description = "Public connection endpoints for all 5 Payment services"
}
