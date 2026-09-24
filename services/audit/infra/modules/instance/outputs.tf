/*
ALGORITHM:
1. Export Instance Template ID, name, and self-link
2. Export Service Account email and ID
3. Export enabled Google Cloud services list
*/

output "template_id" {
  value       = google_compute_instance_template.user_instance_template.id
  description = "ID of the created instance template"
}

output "template_name" {
  value       = google_compute_instance_template.user_instance_template.name
  description = "Name of the created instance template"
}

output "template_self_link" {
  value       = google_compute_instance_template.user_instance_template.self_link
  description = "Self link of the created instance template"
}

output "service_account_email" {
  value       = google_service_account.user_instance_sa.email
  description = "Email of the dedicated least-privilege service account"
}

output "service_account_id" {
  value       = google_service_account.user_instance_sa.id
  description = "ID of the created service account"
}

output "enabled_services" {
  value       = [for s in google_project_service.required_services : s.service]
  description = "List of Google Cloud APIs successfully enabled"
}
