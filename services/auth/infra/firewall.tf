resource "google_compute_firewall" "allow_internal" {
  name    = "${var.vpc_name}-allow-internal"
  network = google_compute_network.auth_vpc.name

  allow {
    protocol = "icmp"
  }

  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }

  source_ranges = [var.subnet_cidr]
}

resource "google_compute_firewall" "allow_ssh" {
  name    = "${var.vpc_name}-allow-ssh"
  network = google_compute_network.auth_vpc.name

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = var.allowed_source_ranges
}

resource "google_compute_firewall" "allow_auth_services" {
  name    = "${var.vpc_name}-allow-auth-services"
  network = google_compute_network.auth_vpc.name

  allow {
    protocol = "tcp"
    ports    = ["5432", "6379", "9092", "4317", "4318", "31426"]
  }

  source_ranges = var.allowed_source_ranges
  target_tags   = ["llmobs-auth-node"]
}
