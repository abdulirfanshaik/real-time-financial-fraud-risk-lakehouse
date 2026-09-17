variable "aws_region" {
  description = "AWS region for the demonstration data platform."
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Resource-name prefix."
  type        = string
  default     = "financial-fraud-risk"
}

