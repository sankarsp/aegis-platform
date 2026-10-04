variable "region" {
  description = "AWS region. Bedrock Titan Text Embeddings v2 must be available and enabled here."
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Short environment name, used in resource names (dev, uat, prod)."
  type        = string
  default     = "dev"
}

variable "vpc_cidr" {
  type    = string
  default = "10.40.0.0/16"
}

variable "api_image_tag" {
  description = "Tag of the API image in ECR to run. CI sets this to the commit SHA."
  type        = string
  default     = "latest"
}

variable "api_desired_count" {
  type    = number
  default = 2
}

variable "api_cpu" {
  type    = number
  default = 512
}

variable "api_memory" {
  type    = number
  default = 1024
}

variable "aurora_min_acu" {
  description = "Aurora Serverless v2 minimum capacity (ACUs)."
  type        = number
  default     = 0.5
}

variable "aurora_max_acu" {
  type    = number
  default = 4
}

variable "seed_demo_data" {
  description = "Load the fictional Northwind Pay demo data on first start. Set false for real tenants."
  type        = bool
  default     = true
}

variable "demo_reviewer_email" {
  description = "When demo data is seeded, this person's Recertification inbox holds the sample review items. Use your sign-in email."
  type        = string
  default     = "priya.nair@northwindpay.example"
}

variable "bedrock_chat_model_id" {
  description = "Optional Bedrock model or inference profile ID used to draft answers in Ask Aegis. Empty disables drafting; retrieval still works."
  type        = string
  default     = ""
}

variable "cognito_domain_prefix" {
  description = "Globally unique prefix for the Cognito hosted sign-in domain."
  type        = string
}

variable "extra_callback_urls" {
  description = "Additional sign-in callback URLs, for example http://localhost:5173/ for local development."
  type        = list(string)
  default     = ["http://localhost:5173/"]
}

variable "deletion_protection" {
  description = "Protect the database from deletion. Keep true outside throwaway environments."
  type        = bool
  default     = true
}
