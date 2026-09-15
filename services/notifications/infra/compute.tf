resource "google_compute_address" "notification_ip" {
  name   = "${var.instance_name}-ip"
  region = var.gcp_region
}

resource "google_compute_instance" "notification_node" {
  name         = var.instance_name
  machine_type = var.machine_type
  zone         = var.gcp_zone
  tags         = ["llmobs-notification-node"]

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
      size  = 50
      type  = "pd-ssd"
    }
  }

  network_interface {
    network    = google_compute_network.notification_vpc.name
    subnetwork = google_compute_subnetwork.notification_subnet.name
    access_config {
      nat_ip = google_compute_address.notification_ip.address
    }
  }

  metadata = {
    startup-script = <<-EOF
      #!/usr/bin/env bash
      set -e

      apt-get update
      apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release git netcat-openbsd

      mkdir -p /etc/apt/keyrings
      curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
      echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
      apt-get update
      apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

      systemctl enable docker
      systemctl start docker
    EOF
  }

  service_account {
    scopes = ["cloud-platform"]
  }
}
