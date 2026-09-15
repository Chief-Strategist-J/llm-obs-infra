output "vpc_name" {
  value       = google_compute_network.user_vpc.name
  description = "Provisioned GCP VPC Network Name"
}

output "subnet_name" {
  value       = google_compute_subnetwork.user_subnet.name
  description = "Provisioned GCP Subnet Name"
}

output "user_node_public_ip" {
  value       = google_compute_address.user_ip.address
  description = "External Static IP address of the GCP User Infrastructure Node"
}

output "user_node_private_ip" {
  value       = google_compute_instance.user_node.network_interface[0].network_ip
  description = "Internal Private IP address of the GCP User Infrastructure Node"
}

output "ssh_connection_command" {
  value       = "gcloud compute ssh ${google_compute_instance.user_node.name} --zone=${var.gcp_zone} --project=${var.gcp_project_id}"
  description = "gcloud SSH command to access the deployment node"
}

output "service_endpoints" {
  value = {
    database         = "${google_compute_address.user_ip.address}:5435"
    redis_ledger     = "${google_compute_address.user_ip.address}:6382"
    kafka_broker     = "${google_compute_address.user_ip.address}:9095"
    otel_collector   = "http://${google_compute_address.user_ip.address}:4323"
    service_registry = "http://${google_compute_address.user_ip.address}:31429"
  }
  description = "Public connection endpoints for all 5 User services"
}
