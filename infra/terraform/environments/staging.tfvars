# PWBS Staging Environment
# Region: eu-central-1 (Frankfurt)  DSGVO-konform

environment = "staging"
aws_region  = "eu-central-1"

# db_password wird ueber TF_VAR_db_password Umgebungsvariable gesetzt
# NIEMALS echte Passwörter in tfvars committen!