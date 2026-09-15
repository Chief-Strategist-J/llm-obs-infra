resource "google_compute_firewall" "allow_internal" {
  name    = "${var.vpc_name}-allow-internal"
  network = google_compute_network.storage_vpc.name

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
  network = google_compute_network.storage_vpc.name

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = var.allowed_source_ranges
}

resource "google_compute_firewall" "allow_storage_services" {
  name    = "${var.vpc_name}-allow-storage-services"
  network = google_compute_network.storage_vpc.name

  allow {
    protocol = "tcp"
    ports    = ["5436", "6383", "9096", "4325", "4326", "31430"]
  }

  source_ranges = var.allowed_source_ranges
  target_tags   = ["llmobs-storage-node"]
}
