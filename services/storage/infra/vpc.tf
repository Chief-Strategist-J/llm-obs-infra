resource "google_compute_network" "storage_vpc" {
  name                    = var.vpc_name
  auto_create_subnetworks = false
  description             = "Dedicated VPC network for LLMObs Storage Infrastructure Stack"
}

resource "google_compute_subnetwork" "storage_subnet" {
  name                     = "${var.vpc_name}-subnet"
  ip_cidr_range            = var.subnet_cidr
  region                   = var.gcp_region
  network                  = google_compute_network.storage_vpc.id
  private_ip_google_access = true
}
