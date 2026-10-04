# FastAPI service on ECS Fargate in private subnets, behind an internal ALB that only CloudFront can reach.

resource "aws_ecr_repository" "api" {
  name                 = "${local.name}-api"
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration {
    scan_on_push = true
  }
  encryption_configuration {
    encryption_type = "KMS"
    kms_key         = aws_kms_key.data.arn
  }
}

resource "aws_ecr_lifecycle_policy" "api" {
  repository = aws_ecr_repository.api.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1, description = "Keep the last 30 images",
      selection    = { tagStatus = "any", countType = "imageCountMoreThan", countNumber = 30 },
      action       = { type = "expire" }
    }]
  })
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/aegis/${var.environment}/api"
  retention_in_days = 365
}

resource "aws_ecs_cluster" "main" {
  name = local.name
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_security_group" "alb" {
  name        = "${local.name}-alb"
  description = "Internal ALB. CloudFront reaches it through VPC origin interfaces inside this VPC."
  vpc_id      = aws_vpc.main.id
  ingress {
    description = "HTTP from CloudFront VPC origin interfaces"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }
  egress {
    description = "To API tasks"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }
}

resource "aws_security_group" "api" {
  name        = "${local.name}-api"
  description = "API tasks"
  vpc_id      = aws_vpc.main.id
  egress {
    description = "HTTPS (ECR, Secrets Manager, Cognito JWKS, Bedrock) and PostgreSQL"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group_rule" "api_from_alb" {
  type                     = "ingress"
  description              = "API port from the ALB"
  security_group_id        = aws_security_group.api.id
  source_security_group_id = aws_security_group.alb.id
  from_port                = 8000
  to_port                  = 8000
  protocol                 = "tcp"
}

resource "aws_lb" "api" {
  name                       = "${local.name}-api"
  internal                   = true
  load_balancer_type         = "application"
  subnets                    = aws_subnet.private[*].id
  security_groups            = [aws_security_group.alb.id]
  drop_invalid_header_fields = true
}

resource "aws_lb_target_group" "api" {
  name        = "${local.name}-api"
  port        = 8000
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = aws_vpc.main.id
  health_check {
    path                = "/health"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 15
  }
  deregistration_delay = 20
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.api.arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}

resource "aws_ecs_task_definition" "api" {
  family                   = "${local.name}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.api_cpu
  memory                   = var.api_memory
  execution_role_arn       = aws_iam_role.task_execution.arn
  task_role_arn            = aws_iam_role.task.arn
  runtime_platform {
    cpu_architecture        = "X86_64"
    operating_system_family = "LINUX"
  }
  container_definitions = jsonencode([{
    name                   = "api"
    image                  = "${aws_ecr_repository.api.repository_url}:${var.api_image_tag}"
    essential              = true
    portMappings           = [{ containerPort = 8000, protocol = "tcp" }]
    readonlyRootFilesystem = false
    environment = [
      { name = "AEGIS_DB_HOST", value = aws_rds_cluster.main.endpoint },
      { name = "AEGIS_DB_NAME", value = aws_rds_cluster.main.database_name },
      { name = "AEGIS_DB_SECRET_ARN", value = aws_rds_cluster.main.master_user_secret[0].secret_arn },
      { name = "AEGIS_EMBEDDING_PROVIDER", value = "bedrock" },
      { name = "AEGIS_AWS_REGION", value = var.region },
      { name = "AEGIS_BEDROCK_CHAT_MODEL_ID", value = var.bedrock_chat_model_id },
      { name = "AEGIS_SEED_DEMO_DATA", value = tostring(var.seed_demo_data) },
      { name = "AEGIS_DEMO_REVIEWER_EMAIL", value = var.demo_reviewer_email },
      { name = "AEGIS_COGNITO_USER_POOL_ID", value = aws_cognito_user_pool.main.id },
      { name = "AEGIS_COGNITO_CLIENT_ID", value = aws_cognito_user_pool_client.web.id },
      { name = "AEGIS_CORS_ORIGINS", value = jsonencode(["https://${aws_cloudfront_distribution.web.domain_name}"]) },
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.api.name
        awslogs-region        = var.region
        awslogs-stream-prefix = "api"
      }
    }
  }])
}

resource "aws_ecs_service" "api" {
  name                              = "api"
  cluster                           = aws_ecs_cluster.main.id
  task_definition                   = aws_ecs_task_definition.api.arn
  desired_count                     = var.api_desired_count
  launch_type                       = "FARGATE"
  health_check_grace_period_seconds = 60
  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.api.id]
    assign_public_ip = false
  }
  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8000
  }
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
  depends_on = [aws_lb_listener.http, aws_rds_cluster_instance.main]
}

resource "aws_appautoscaling_target" "api" {
  service_namespace  = "ecs"
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.api.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  min_capacity       = var.api_desired_count
  max_capacity       = var.api_desired_count * 3
}

resource "aws_appautoscaling_policy" "api_cpu" {
  name               = "${local.name}-api-cpu"
  service_namespace  = aws_appautoscaling_target.api.service_namespace
  resource_id        = aws_appautoscaling_target.api.resource_id
  scalable_dimension = aws_appautoscaling_target.api.scalable_dimension
  policy_type        = "TargetTrackingScaling"
  target_tracking_scaling_policy_configuration {
    target_value = 60
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
  }
}
