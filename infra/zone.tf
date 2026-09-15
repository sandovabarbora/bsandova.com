resource "cloudflare_zone" "site" {
  name    = "bsandova.com"
  account = { id = var.account_id }
  type    = "full"
}
