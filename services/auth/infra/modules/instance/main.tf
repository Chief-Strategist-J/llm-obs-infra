/*
ALGORITHM:
1. Enable declared required Google Cloud project services and APIs
2. Provision dedicated Service Account for least-privilege instance execution
3. Assign defined minimal IAM roles to the Service Account
4. Resolve latest OS base image from configured project and family
5. Provision Compute Instance Template specifying hardware, disk, least-privilege SA, and startup script
*/

resource "google_project_service" "required_services" {
  for_each                   = toset(var.gcp_services)
  project                    = var.project_id
  service                    = each.value
  disable_on_destroy         = false
  disable_dependent_services = false
}

resource "google_service_account" "user_instance_sa" {
  account_id   = var.service_account_id
  display_name = var.service_account_display_name
  description  = "Least-privilege Service Account for LLMObs User Service compute nodes"
  project      = var.project_id

  depends_on = [google_project_service.required_services]
}

resource "google_project_iam_member" "sa_roles" {
  for_each = toset(var.service_account_roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.user_instance_sa.email}"

  depends_on = [google_service_account.user_instance_sa]
}

data "google_compute_image" "base_image" {
  family  = var.image_family
  project = var.image_project
}

resource "google_compute_instance_template" "user_instance_template" {
  name_prefix  = var.template_name_prefix
  description  = "Instance template for scalable LLMObs User service nodes"
  project      = var.project_id
  machine_type = var.machine_type
  tags         = var.tags
  labels       = var.labels

  disk {
    source_image = data.google_compute_image.base_image.self_link
    auto_delete  = true
    boot         = true
    disk_size_gb = var.disk_size_gb
    disk_type    = var.disk_type
  }

  network_interface {
    network    = var.network_id
    subnetwork = var.subnetwork_id

    dynamic "access_config" {
      for_each = var.assign_public_ip ? [1] : []
      content {
        network_tier = "PREMIUM"
      }
    }
  }

  service_account {
    email  = google_service_account.user_instance_sa.email
    scopes = var.service_account_scopes
  }

  metadata = {
    startup-script = var.startup_script != "" ? var.startup_script : file("${path.module}/files/startup.sh")
    enable-oslogin = var.enable_oslogin ? "TRUE" : "FALSE"
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [
    google_project_service.required_services,
    google_project_iam_member.sa_roles
  ]
}
