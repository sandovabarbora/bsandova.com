variable "account_id" {
  type    = string
  default = "bb15909c261e2334fa1e4815e0920dbb"
}

variable "zone_id" {
  type    = string
  default = "d23e1ce5ed08615e4477623eb4c17a3a"
}

# Wedos web hosting, left in place from the registrar's DNS scan. The Worker route
# *bsandova.com/* answers before these are ever reached; they exist so the names are
# proxied and the zone has something to point at.
variable "placeholder_ipv4" {
  type    = string
  default = "185.8.237.22"
}

variable "placeholder_ipv6" {
  type    = string
  default = "2a0e:acc0::d22"
}
