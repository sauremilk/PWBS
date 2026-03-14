# PWBS – ECS Fargate Module (TASK-146)
# Backend API + Celery Workers auf ECS Fargate
# ALB for horizontal scaling, health checks, session-free routing

# ---------------------------------------------------------------------------
# Security Groups
# ---------------------------------------------------------------------------

resource "aws_security_group" "alb" {
  name_prefix = "${var.project}-${var.environment}-alb-"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS from internet"
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP redirect"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, { Name = "${var.project}-${var.environment}-alb-sg" })
}

resource "aws_security_group" "api" {
  name_prefix = "${var.project}-${var.environment}-api-"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
    description     = "API traffic from ALB"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, { Name = "${var.project}-${var.environment}-api-sg" })
}

# ---------------------------------------------------------------------------
# Application Load Balancer
# ---------------------------------------------------------------------------

resource "aws_lb" "api" {
  name               = "${var.project}-${var.environment}-api"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.public_subnet_ids

  enable_deletion_protection = var.environment == "production"

  tags = merge(var.tags, { Name = "${var.project}-${var.environment}-alb" })
}

resource "aws_lb_target_group" "api" {
  name        = "${var.project}-${var.environment}-api-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    path                = "/api/v1/admin/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    matcher             = "200"
  }

  deregistration_delay = 30

  tags = var.tags
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.api.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.acm_certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}

resource "aws_lb_listener" "http_redirect" {
  load_balancer_arn = aws_lb.api.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"

    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

# ---------------------------------------------------------------------------
# ECS Cluster
# ---------------------------------------------------------------------------

resource "aws_ecs_cluster" "main" {
  name = "${var.project}-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = var.tags
}

# ---------------------------------------------------------------------------
# API Task Definition + Service (3+ instances)
# ---------------------------------------------------------------------------

resource "aws_ecs_task_definition" "api" {
  family                   = "${var.project}-${var.environment}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.api_cpu
  memory                   = var.api_memory
  execution_role_arn       = var.execution_role_arn
  task_role_arn            = var.task_role_arn

  container_definitions = jsonencode([{
    name      = "api"
    image     = var.backend_image
    essential = true
    command   = ["uvicorn", "pwbs.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

    portMappings = [{
      containerPort = 8000
      protocol      = "tcp"
    }]

    environment = var.api_environment

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = var.log_group
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "api"
      }
    }
  }])

  tags = var.tags
}

resource "aws_ecs_service" "api" {
  name            = "${var.project}-${var.environment}-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.api_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = var.private_subnet_ids
    security_groups = [aws_security_group.api.id]
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8000
  }

  deployment_configuration {
    maximum_percent         = 200
    minimum_healthy_percent = 100
  }

  depends_on = [aws_lb_listener.https]

  tags = var.tags
}

# --- Celery Worker Task Definitions (TASK-121) ---

resource "aws_ecs_task_definition" "celery_worker_ingestion" {
  family                   = "${var.project}-${var.environment}-celery-ingestion"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024

  container_definitions = jsonencode([{
    name      = "celery-ingestion"
    image     = var.backend_image
    essential = true
    command   = ["celery", "-A", "pwbs.queue.celery_app", "worker", "-Q", "ingestion.high,ingestion.bulk", "-c", "4", "--loglevel=info"]
    environment = var.worker_environment
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = var.log_group
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "celery-ingestion"
      }
    }
  }])

  tags = var.tags
}

resource "aws_ecs_task_definition" "celery_worker_processing" {
  family                   = "${var.project}-${var.environment}-celery-processing"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 1024
  memory                   = 2048

  container_definitions = jsonencode([{
    name      = "celery-processing"
    image     = var.backend_image
    essential = true
    command   = ["celery", "-A", "pwbs.queue.celery_app", "worker", "-Q", "processing.embed,processing.extract", "-c", "2", "--loglevel=info"]
    environment = var.worker_environment
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = var.log_group
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "celery-processing"
      }
    }
  }])

  tags = var.tags
}

resource "aws_ecs_task_definition" "celery_worker_briefing" {
  family                   = "${var.project}-${var.environment}-celery-briefing"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024

  container_definitions = jsonencode([{
    name      = "celery-briefing"
    image     = var.backend_image
    essential = true
    command   = ["celery", "-A", "pwbs.queue.celery_app", "worker", "-Q", "briefing.generate", "-c", "2", "--loglevel=info"]
    environment = var.worker_environment
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = var.log_group
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "celery-briefing"
      }
    }
  }])

  tags = var.tags
}

resource "aws_ecs_task_definition" "celery_beat" {
  family                   = "${var.project}-${var.environment}-celery-beat"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512

  container_definitions = jsonencode([{
    name      = "celery-beat"
    image     = var.backend_image
    essential = true
    command   = ["celery", "-A", "pwbs.queue.celery_app", "beat", "--loglevel=info"]
    environment = var.worker_environment
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = var.log_group
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "celery-beat"
      }
    }
  }])

  tags = var.tags
}
