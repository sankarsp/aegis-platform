# Sign-in for the console: Cognito user pool with the hosted UI. The React app uses the
# authorization code flow with PKCE and sends the ID token to the API.

resource "aws_cognito_user_pool" "main" {
  name                     = local.name
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]
  mfa_configuration        = "ON"
  software_token_mfa_configuration {
    enabled = true
  }
  password_policy {
    minimum_length                   = 14
    require_lowercase                = true
    require_uppercase                = true
    require_numbers                  = true
    require_symbols                  = true
    temporary_password_validity_days = 3
  }
  admin_create_user_config {
    allow_admin_create_user_only = true # users are provisioned by the client's admins or SSO
  }
  schema {
    name                = "name"
    attribute_data_type = "String"
    required            = true
    mutable             = true
  }
  deletion_protection = var.deletion_protection ? "ACTIVE" : "INACTIVE"
}

resource "aws_cognito_user_pool_domain" "main" {
  domain       = var.cognito_domain_prefix
  user_pool_id = aws_cognito_user_pool.main.id
}

resource "aws_cognito_user_pool_client" "web" {
  name                                 = "${local.name}-web"
  user_pool_id                         = aws_cognito_user_pool.main.id
  generate_secret                      = false
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email", "profile"]
  supported_identity_providers         = ["COGNITO"]
  # Hosted UI sign-in only: no direct API sign-in, so users cannot mint tokens that edit their own attributes.
  explicit_auth_flows    = ["ALLOW_REFRESH_TOKEN_AUTH"]
  callback_urls          = concat(["https://${aws_cloudfront_distribution.web.domain_name}/"], var.extra_callback_urls)
  logout_urls            = concat(["https://${aws_cloudfront_distribution.web.domain_name}/"], var.extra_callback_urls)
  id_token_validity      = 60
  access_token_validity  = 60
  refresh_token_validity = 12
  token_validity_units {
    id_token      = "minutes"
    access_token  = "minutes"
    refresh_token = "hours"
  }
  prevent_user_existence_errors = "ENABLED"
}

# Roles. Users with no group can read everything and answer their own review items.
resource "aws_cognito_user_group" "roles" {
  for_each = {
    "aegis-steward"  = "Sign off lineage, resolve issues, confirm labels, run tests, assign owners"
    "aegis-approver" = "Record model approval steps, pause or resume models, seal campaigns"
    "aegis-admin"    = "Change access policies, rebuild the search index, seal campaigns"
  }
  name         = each.key
  description  = each.value
  user_pool_id = aws_cognito_user_pool.main.id
}
