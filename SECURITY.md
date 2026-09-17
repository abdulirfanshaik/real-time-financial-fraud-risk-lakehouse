# Security Policy

## Data handling

This repository contains synthetic data only. Do not commit real customer data, account numbers, card numbers, credentials, tokens, internal hostnames or proprietary schemas.

## Secrets

Use environment variables or a managed secret store. Copy `.env.example` to a local `.env` only for development; `.env` is ignored by Git. Never place cloud keys or Snowflake credentials in source files, Terraform variables or CI configuration.

## Reporting a vulnerability

Open a private security advisory in the GitHub repository rather than a public issue. Include the affected component, reproduction steps and expected impact. Do not include sensitive production information.

