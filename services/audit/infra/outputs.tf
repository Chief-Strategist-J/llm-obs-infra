output "vpc_name" {
  value       = google_compute_network.audit_vpc.name
  description = "Provisioned GCP VPC Network Name"
}

output "subnet_name" {
  value       = google_compute_subnetwork.audit_subnet.name
  description = "Provisioned GCP Subnet Name"
}

output "audit_node_public_ip" {
  value       = google_compute_address.audit_ip.address
  description = "External Static IP address of the GCP Audit Infrastructure Node"
}

output "audit_node_private_ip" {
  value       = google_compute_instance.audit_node.network_interface[0].network_ip
  description = "Internal Private IP address of the GCP Audit Infrastructure Node"
}

output "ssh_connection_command" {
  value       = "gcloud compute ssh ${google_compute_instance.audit_node.name} --zone=${var.gcp_zone} --project=${var.gcp_project_id}"
  description = "gcloud SSH command to access the deployment node"
}

output "service_endpoints" {
  value = {
    database         = "${google_compute_address.audit_ip.address}:5437"
    redis_ledger     = "${google_compute_address.audit_ip.address}:6384"
    kafka_broker     = "${google_compute_address.audit_ip.address}:9097"
    otel_collector   = "http://${google_compute_address.audit_ip.address}:4327"
    service_registry = "http://${google_compute_address.audit_ip.address}:31431"
  }
  description = "Public connection endpoints for all 5 Audit services"
}
