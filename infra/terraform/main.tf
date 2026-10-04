terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.82, < 7.0" # 5.82 adds CloudFront VPC origins
    }
  }

  # Remote state in S3. Supply settings at init: terraform init -backend-config=backend.hcl
  backend "s3" {}
}

provider "aws" {
  region = var.region
  default_tags {
    tags = {
      Application = "aegis"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

data "aws_caller_identity" "current" {}
data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  name = "aegis-${var.environment}"
  azs  = slice(data.aws_availability_zones.available.names, 0, 2)
}
