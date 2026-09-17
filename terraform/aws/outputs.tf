output "lakehouse_bucket" {
  value       = aws_s3_bucket.lakehouse.id
  description = "Encrypted S3 bucket for Bronze, Silver and Gold data."
}

output "glue_database" {
  value       = aws_glue_catalog_database.financial_risk.name
  description = "Glue Data Catalog database name."
}

output "pipeline_log_group" {
  value       = aws_cloudwatch_log_group.pipeline.name
  description = "CloudWatch log group for pipeline observability."
}

