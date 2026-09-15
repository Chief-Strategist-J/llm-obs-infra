output "vpc_name" {
  value       = google_compute_network.notification_vpc.name
  description = "Provisioned GCP VPC Network Name"
}

output "subnet_name" {
  value       = google_compute_subnetwork.notification_subnet.name
  description = "Provisioned GCP Subnet Name"
}

output "notification_node_public_ip" {
  value       = google_compute_address.notification_ip.address
  description = "External Static IP address of the GCP Notification Infrastructure Node"
}

output "notification_node_private_ip" {
  value       = google_compute_instance.notification_node.network_interface[0].network_ip
  description = "Internal Private IP address of the GCP Notification Infrastructure Node"
}

output "ssh_connection_command" {
  value       = "gcloud compute ssh ${google_compute_instance.notification_node.name} --zone=${var.gcp_zone} --project=${var.gcp_project_id}"
  description = "gcloud SSH command to access the deployment node"
}

output "service_endpoints" {
  value = {
    database         = "${google_compute_address.notification_ip.address}:5434"
    redis_ledger     = "${google_compute_address.notification_ip.address}:6381"
    kafka_broker     = "${google_compute_address.notification_ip.address}:9094"
    otel_collector   = "http://${google_compute_address.notification_ip.address}:4321"
    service_registry = "http://${google_compute_address.notification_ip.address}:31428"
  }
  description = "Public connection endpoints for all 5 Notification services"
}
