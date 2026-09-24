/*
ALGORITHM:
1. Declare VPC network and subnetwork identification variables
2. Declare CIDR block and GCP regional variables
3. Declare ingress rules, source ranges, allowed ports, and target tags
4. Declare Cloud NAT toggle parameter
*/

variable "vpc_name" {
  type        = string
  description = "Name of the custom VPC network"
}

variable "subnet_name" {
  type        = string
  description = "Name of the subnetwork"
}

variable "subnet_cidr" {
  type        = string
  description = "CIDR block IP range for the subnet"
}

variable "region" {
  type        = string
  description = "GCP region where the subnetwork resides"
}

variable "allowed_source_ranges" {
  type        = list(string)
  description = "CIDR blocks allowed for service ingress traffic"
}

variable "ssh_allowed_source_ranges" {
  type        = list(string)
  description = "CIDR blocks allowed for SSH access"
}

variable "service_ports" {
  type        = list(string)
  description = "List of TCP ports exposed by the User stack services"
}

variable "target_tags" {
  type        = list(string)
  description = "Target network tags to apply firewall ingress rules"
}

variable "enable_nat" {
  type        = bool
  description = "Whether to deploy Cloud Router and Cloud NAT for outbound internet access"
  default     = true
}
