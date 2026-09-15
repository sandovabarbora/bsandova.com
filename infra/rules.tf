# www → apex, permanent, query string kept. Created 2026-09-15 via the API, imported here.
resource "cloudflare_ruleset" "redirects" {
  zone_id = var.zone_id
  name    = "default"
  kind    = "zone"
  phase   = "http_request_dynamic_redirect"

  rules = [{
    description = "www to apex, permanent"
    expression  = "(http.host eq \"www.bsandova.com\")"
    action      = "redirect"
    enabled     = true
    action_parameters = {
      from_value = {
        status_code           = 301
        preserve_query_string = true
        target_url            = { expression = "concat(\"https://bsandova.com\", http.request.uri.path)" }
      }
    }
  }]
}

# Security headers on every response. The site is static and self-contained: no frames,
# no cross-origin embedding, no sensors. HSTS one year with subdomains (all of them are
# proxied and served by the same Worker).
resource "cloudflare_ruleset" "headers" {
  zone_id = var.zone_id
  name    = "security headers"
  kind    = "zone"
  phase   = "http_response_headers_transform"

  rules = [{
    description = "security headers on every response"
    expression  = "true"
    action      = "rewrite"
    enabled     = true
    action_parameters = {
      headers = {
        "Strict-Transport-Security" = { operation = "set", value = "max-age=31536000; includeSubDomains" }
        "X-Content-Type-Options"    = { operation = "set", value = "nosniff" }
        "X-Frame-Options"           = { operation = "set", value = "DENY" }
        "Referrer-Policy"           = { operation = "set", value = "strict-origin-when-cross-origin" }
        "Permissions-Policy"        = { operation = "set", value = "camera=(), microphone=(), geolocation=(), interest-cohort=()" }
      }
    }
  }]
}
