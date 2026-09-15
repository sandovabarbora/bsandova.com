terraform {
  required_version = ">= 1.9"
  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 5.0"
    }
  }
}

# Auth: CLOUDFLARE_API_TOKEN in the environment (Zone: DNS Edit, Dynamic Redirect Edit,
# Transform Rules Edit, Zone Settings Edit). State stays local and out of git; one zone,
# one operator, no remote backend.
provider "cloudflare" {}
