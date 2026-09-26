/*
ALGORITHM:
1. Provision TCP Health Check for auto-healing and node liveness monitoring
2. Provision Managed Instance Group (MIG) backed by Instance Template
3. Map named ports for service endpoints
4. Attach auto-healing policy referencing the health check
5. Provision Compute Autoscaler with min/max replicas and CPU utilization target
*/

resource "google_compute_health_check" "user_health_check" {
  name                = "${var.base_instance_name}-health-check"
  project             = var.project_id
  check_interval_sec  = var.health_check_interval_sec
  timeout_sec         = var.health_check_timeout_sec
  healthy_threshold   = var.healthy_threshold
  unhealthy_threshold = var.unhealthy_threshold

  tcp_health_check {
    port = var.health_check_port
  }
}

resource "google_compute_instance_group_manager" "user_igm" {
  name               = "${var.base_instance_name}-igm"
  project            = var.project_id
  zone               = var.zone
  base_instance_name = var.base_instance_name
  target_size        = var.target_size

  version {
    instance_template = var.instance_template_self_link
    name              = "primary"
  }

  dynamic "named_port" {
    for_each = var.named_ports
    content {
      name = named_port.value.name
      port = named_port.value.port
    }
  }

  auto_healing_policies {
    health_check      = google_compute_health_check.user_health_check.id
    initial_delay_sec = var.health_check_initial_delay_sec
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "google_compute_autoscaler" "user_autoscaler" {
  name    = "${var.base_instance_name}-autoscaler"
  project = var.project_id
  zone    = var.zone
  target  = google_compute_instance_group_manager.user_igm.id

  autoscaling_policy {
    min_replicas    = var.min_replicas
    max_replicas    = var.max_replicas
    cooldown_period = var.cooldown_period_sec

    cpu_utilization {
      target = var.target_cpu_utilization
    }
  }
}
