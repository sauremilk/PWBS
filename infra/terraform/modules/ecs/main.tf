# PWBS – ECS Fargate Module
# Backend API + Celery Workers auf ECS Fargate (TASK-121)

# Skelett – API task definition wird in TASK-040+ befuellt

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
