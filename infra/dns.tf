locals {
  names = {
    apex = "bsandova.com"
    www  = "www.bsandova.com"
    wild = "*.bsandova.com"
  }
}

resource "cloudflare_dns_record" "a" {
  for_each = local.names
  zone_id  = var.zone_id
  name     = each.value
  type     = "A"
  content  = var.placeholder_ipv4
  proxied  = true
  ttl      = 1
}

resource "cloudflare_dns_record" "aaaa" {
  for_each = local.names
  zone_id  = var.zone_id
  name     = each.value
  type     = "AAAA"
  content  = var.placeholder_ipv6
  proxied  = true
  ttl      = 1
}

# The two _acme-challenge TXT records are Cloudflare's own (Universal SSL validation);
# they are not managed here on purpose.
