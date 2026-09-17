provider "aws" {
  region = var.aws_region
}

resource "random_id" "suffix" {
  byte_length = 4
}

locals {
  name = "${var.project_name}-${var.environment}-${random_id.suffix.hex}"
  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
    DataClass   = "Synthetic"
  }
}

resource "aws_s3_bucket" "lakehouse" {
  bucket = local.name
  tags   = local.tags
}

resource "aws_s3_bucket_public_access_block" "lakehouse" {
  bucket                  = aws_s3_bucket.lakehouse.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "lakehouse" {
  bucket = aws_s3_bucket.lakehouse.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_versioning" "lakehouse" {
  bucket = aws_s3_bucket.lakehouse.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_glue_catalog_database" "financial_risk" {
  name = replace("${var.project_name}_${var.environment}", "-", "_")
}

resource "aws_cloudwatch_log_group" "pipeline" {
  name              = "/data-platform/${var.project_name}/${var.environment}"
  retention_in_days = 30
  tags              = local.tags
}

resource "aws_iam_policy" "lakehouse_job" {
  name = "${local.name}-job-policy"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"]
        Resource = [
          aws_s3_bucket.lakehouse.arn,
          "${aws_s3_bucket.lakehouse.arn}/*"
        ]
      },
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "${aws_cloudwatch_log_group.pipeline.arn}:*"
      }
    ]
  })
  tags = local.tags
}

