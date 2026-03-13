# PWBS Production Environment
# Region: eu-central-1 (Frankfurt)  DSGVO-konform

environment = "production"
aws_region  = "eu-central-1"

# db_password wird ueber TF_VAR_db_password Umgebungsvariable gesetzt
# NIEMALS echte Passwörter in tfvars committen!