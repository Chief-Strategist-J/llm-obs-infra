/*
ALGORITHM:
1. Define service identifier (service_name) for automated resource prefixing
2. Define GCP provider coordinates (project, region, zone)
3. Define Google API dependencies and least-privilege IAM roles and scopes
4. Define network topology, CIDR block, and firewall port whitelist
5. Define VM instance specifications: machine type, OS image, disk size, and type
6. Define horizontal autoscaling parameters and compute health checks
*/

service_name = "auth"

gcp_project_id = "your-gcp-project-id"
gcp_region     = "us-central1"
gcp_zone       = "us-central1-a"

gcp_services = [
  "compute.googleapis.com",
  "iam.googleapis.com",
  "cloudresourcemanager.googleapis.com",
  "logging.googleapis.com",
  "monitoring.googleapis.com"
]

service_account_roles = [
  "roles/logging.logWriter",
  "roles/monitoring.metricWriter",
  "roles/monitoring.viewer"
]

service_account_scopes = [
  "https://www.googleapis.com/auth/logging.write",
  "https://www.googleapis.com/auth/monitoring.write"
]

subnet_cidr = "10.0.10.0/24"
enable_nat  = true

allowed_source_ranges     = ["0.0.0.0/0"]
ssh_allowed_source_ranges = ["0.0.0.0/0"]

service_ports = ["5432", "6379", "9092", "4317", "4318", "31426"]

machine_type     = "e2-standard-4"
image_family     = "ubuntu-2204-lts"
image_project    = "ubuntu-os-cloud"
disk_size_gb     = 50
disk_type        = "pd-ssd"
assign_public_ip = true
enable_oslogin   = true

instance_labels = {
  environment = "development"
  managed_by  = "terraform"
}

target_size                    = 1
min_replicas                   = 1
max_replicas                   = 3
cooldown_period_sec            = 60
target_cpu_utilization         = 0.70
health_check_port              = 22
health_check_interval_sec      = 15
health_check_timeout_sec       = 5
healthy_threshold              = 2
unhealthy_threshold            = 3
health_check_initial_delay_sec = 300

named_ports = [
  { name = "database", port = 5432 },
  { name = "redis", port = 6379 },
  { name = "kafka", port = 9092 },
  { name = "otel", port = 4317 },
  { name = "registry", port = 31426 }
]
