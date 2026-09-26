/*
ALGORITHM:
1. Initialize Google Cloud provider using project, region, and zone inputs
2. Calculate service-derived resource names from service_name input
3. Invoke Network module to provision VPC, Subnet, Cloud NAT, and firewall rules
4. Invoke Instance module to enable APIs, create least-privilege SA, and configure Instance Template
5. Invoke Compute module to provision Managed Instance Group and horizontal Autoscaler
*/

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.20.0"
    }
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
  zone    = var.gcp_zone
}

locals {
  service_name         = var.service_name
  computed_vpc_name    = var.vpc_name != "" ? var.vpc_name : "llmobs-${local.service_name}-vpc"
  computed_subnet_name = var.subnet_name != "" ? var.subnet_name : "llmobs-${local.service_name}-subnet"
  computed_sa_id       = var.service_account_id != "" ? var.service_account_id : "llmobs-${local.service_name}-sa"
  computed_node_name   = var.instance_name != "" ? var.instance_name : "llmobs-${local.service_name}-node"
  computed_tpl_prefix  = "llmobs-${local.service_name}-tpl-"
  computed_tags        = length(var.network_tags) > 0 ? var.network_tags : ["llmobs-${local.service_name}-node"]
}

module "network" {
  source = "./modules/network"

  vpc_name                  = local.computed_vpc_name
  subnet_name               = local.computed_subnet_name
  subnet_cidr               = var.subnet_cidr
  region                    = var.gcp_region
  allowed_source_ranges     = var.allowed_source_ranges
  ssh_allowed_source_ranges = var.ssh_allowed_source_ranges
  service_ports             = var.service_ports
  target_tags               = local.computed_tags
  enable_nat                = var.enable_nat
}

module "instance" {
  source = "./modules/instance"

  project_id                   = var.gcp_project_id
  region                       = var.gcp_region
  gcp_services                 = var.gcp_services
  service_account_id           = local.computed_sa_id
  service_account_display_name = "LLMObs ${local.service_name} Service SA"
  service_account_roles        = var.service_account_roles
  service_account_scopes       = var.service_account_scopes
  template_name_prefix         = local.computed_tpl_prefix
  machine_type                 = var.machine_type
  image_family                 = var.image_family
  image_project                = var.image_project
  disk_size_gb                 = var.disk_size_gb
  disk_type                    = var.disk_type
  network_id                   = module.network.network_self_link
  subnetwork_id                = module.network.subnetwork_self_link
  assign_public_ip             = var.assign_public_ip
  tags                         = local.computed_tags
  labels                       = merge(var.instance_labels, { service = local.service_name })
  startup_script               = var.custom_startup_script
  enable_oslogin               = var.enable_oslogin

  depends_on = [module.network]
}

module "compute" {
  source = "./modules/compute"

  project_id                     = var.gcp_project_id
  zone                           = var.gcp_zone
  base_instance_name             = local.computed_node_name
  instance_template_self_link    = module.instance.template_self_link
  target_size                    = var.target_size
  min_replicas                   = var.min_replicas
  max_replicas                   = var.max_replicas
  cooldown_period_sec            = var.cooldown_period_sec
  target_cpu_utilization         = var.target_cpu_utilization
  named_ports                    = var.named_ports
  health_check_port              = var.health_check_port
  health_check_interval_sec      = var.health_check_interval_sec
  health_check_timeout_sec       = var.health_check_timeout_sec
  healthy_threshold              = var.healthy_threshold
  unhealthy_threshold            = var.unhealthy_threshold
  health_check_initial_delay_sec = var.health_check_initial_delay_sec

  depends_on = [module.instance]
}
