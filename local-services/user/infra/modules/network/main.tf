/*
ALGORITHM:
1. Define custom VPC network with manual subnetwork assignment
2. Create dedicated subnet with private Google access enabled
3. Provision Cloud Router and Cloud NAT for outbound internet connectivity
4. Provision internal firewall rule for inter-service communication within subnet
5. Provision SSH firewall rule restricted to allowed source CIDR ranges
6. Provision service ports firewall rule for User application endpoints
7. Provision GCP health check probe ingress firewall rule for autoscaling
*/

resource "google_compute_network" "user_vpc" {
  name                    = var.vpc_name
  auto_create_subnetworks = false
  description             = "Dedicated VPC network for LLMObs User Infrastructure Stack"
}

resource "google_compute_subnetwork" "user_subnet" {
  name                     = var.subnet_name
  ip_cidr_range            = var.subnet_cidr
  region                   = var.region
  network                  = google_compute_network.user_vpc.id
  private_ip_google_access = true
  description              = "Subnetwork for LLMObs User Stack with Private Google Access"
}

resource "google_compute_router" "user_router" {
  count   = var.enable_nat ? 1 : 0
  name    = "${var.vpc_name}-router"
  region  = var.region
  network = google_compute_network.user_vpc.id
}

resource "google_compute_router_nat" "user_nat" {
  count                              = var.enable_nat ? 1 : 0
  name                               = "${var.vpc_name}-nat"
  router                             = google_compute_router.user_router[0].name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

resource "google_compute_firewall" "allow_internal" {
  name        = "${var.vpc_name}-allow-internal"
  network     = google_compute_network.user_vpc.name
  description = "Allow internal subnet traffic between User stack components"

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
  name        = "${var.vpc_name}-allow-ssh"
  network     = google_compute_network.user_vpc.name
  description = "Allow SSH ingress from allowed source ranges"

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = var.ssh_allowed_source_ranges
  target_tags   = var.target_tags
}

resource "google_compute_firewall" "allow_user_services" {
  name        = "${var.vpc_name}-allow-user-services"
  network     = google_compute_network.user_vpc.name
  description = "Allow ingress traffic to User stack service ports"

  allow {
    protocol = "tcp"
    ports    = var.service_ports
  }

  source_ranges = var.allowed_source_ranges
  target_tags   = var.target_tags
}

resource "google_compute_firewall" "allow_health_checks" {
  name        = "${var.vpc_name}-allow-health-checks"
  network     = google_compute_network.user_vpc.name
  description = "Allow GCP health check probes to monitor instance health"

  allow {
    protocol = "tcp"
    ports    = concat(var.service_ports, ["22", "80", "443"])
  }

  source_ranges = ["35.191.0.0/16", "130.211.0.0/22"]
  target_tags   = var.target_tags
}
