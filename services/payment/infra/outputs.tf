/*
ALGORITHM:
1. Export Network layer identifiers (VPC name, Subnet name, Subnet CIDR)
2. Export Security and Instance layer attributes (Service Account email, enabled APIs, Template link)
3. Export Compute and Scaling parameters (IGM name, Autoscaler name, Scaling policy)
4. Export Cloud operational and deployment commands (list instances, describe group, deploy services)
*/

output "service_name" {
  value       = var.service_name
  description = "Target service stack name"
}

output "vpc_name" {
  value       = module.network.network_name
  description = "Provisioned GCP VPC Network Name"
}

output "subnet_name" {
  value       = module.network.subnetwork_name
  description = "Provisioned GCP Subnet Name"
}

output "subnet_cidr" {
  value       = module.network.subnetwork_cidr
  description = "Provisioned GCP Subnet CIDR block"
}

output "service_account_email" {
  value       = module.instance.service_account_email
  description = "Email of the dedicated least-privilege Service Account attached to the instances"
}

output "enabled_google_services" {
  value       = module.instance.enabled_services
  description = "List of Google Cloud APIs enabled for this infrastructure"
}

output "instance_template_name" {
  value       = module.instance.template_name
  description = "Name of the created Compute Instance Template"
}

output "instance_template_self_link" {
  value       = module.instance.template_self_link
  description = "Self link URI of the Compute Instance Template"
}

output "instance_group_manager_name" {
  value       = module.compute.instance_group_manager_name
  description = "Managed Instance Group Manager Name"
}

output "autoscaler_name" {
  value       = module.compute.autoscaler_name
  description = "Compute Autoscaler Name"
}

output "scaling_policy" {
  value = {
    min_replicas           = module.compute.min_replicas
    max_replicas           = module.compute.max_replicas
    target_cpu_utilization = module.compute.target_cpu_utilization
  }
  description = "Configured autoscaling policy thresholds"
}

output "cloud_commands" {
  value = {
    deploy_services = "bash $(pwd)/scripts/deploy-services.sh"
    list_instances  = "gcloud compute instance-groups list-instances ${module.compute.instance_group_manager_name} --zone=${var.gcp_zone} --project=${var.gcp_project_id}"
    describe_group  = "gcloud compute instance-groups managed describe ${module.compute.instance_group_manager_name} --zone=${var.gcp_zone} --project=${var.gcp_project_id}"
    view_autoscaler = "gcloud compute autoscalers describe ${module.compute.autoscaler_name} --zone=${var.gcp_zone} --project=${var.gcp_project_id}"
  }
  description = "Operational gcloud commands for deployment and monitoring"
}
