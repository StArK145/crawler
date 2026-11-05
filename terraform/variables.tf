variable "aws_region" {
  description = "AWS region to deploy the infrastructure"
  type        = string
  default     = "ap-south-1"
}

variable "public_key_path" {
  description = "Path to the SSH public key for EC2 instance access"
  type        = string
  default     = "~/.ssh/id_ed25519_personal.pub"
}
