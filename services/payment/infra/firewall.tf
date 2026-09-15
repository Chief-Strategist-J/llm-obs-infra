resource "google_compute_firewall" "allow_internal" {
  name    = "${var.vpc_name}-allow-internal"
  network = google_compute_network.payment_vpc.name

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
  network = google_compute_network.payment_vpc.name

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = var.allowed_source_ranges
}

resource "google_compute_firewall" "allow_payment_services" {
  name    = "${var.vpc_name}-allow-payment-services"
  network = google_compute_network.payment_vpc.name

  allow {
    protocol = "tcp"
    ports    = ["5433", "6380", "9093", "4319", "4320", "31427"]
  }

  source_ranges = var.allowed_source_ranges
  target_tags   = ["llmobs-payment-node"]
}
