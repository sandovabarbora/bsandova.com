# Declarative imports of what already exists, so the first plan adopts rather than recreates.
# Safe to delete after the first successful apply.

import {
  to = cloudflare_zone.site
  id = "d23e1ce5ed08615e4477623eb4c17a3a"
}

import {
  to = cloudflare_ruleset.redirects
  id = "zones/d23e1ce5ed08615e4477623eb4c17a3a/4dba659f07e94a709d85d2e2ca99b490"
}

import {
  to = cloudflare_dns_record.a["apex"]
  id = "d23e1ce5ed08615e4477623eb4c17a3a/d7594ece4b1e4999fd97c6b5f26c8097"
}

import {
  to = cloudflare_dns_record.a["www"]
  id = "d23e1ce5ed08615e4477623eb4c17a3a/b0cc788ec2c49027129b5ddfbf3a7471"
}

import {
  to = cloudflare_dns_record.a["wild"]
  id = "d23e1ce5ed08615e4477623eb4c17a3a/96b0ba41e2ea5bf0c62575148cf5fbcc"
}

import {
  to = cloudflare_dns_record.aaaa["apex"]
  id = "d23e1ce5ed08615e4477623eb4c17a3a/009d537b39c8c047e0e07f8b7978fe4f"
}

import {
  to = cloudflare_dns_record.aaaa["www"]
  id = "d23e1ce5ed08615e4477623eb4c17a3a/f856592fe369a8887478377719af11e7"
}

import {
  to = cloudflare_dns_record.aaaa["wild"]
  id = "d23e1ce5ed08615e4477623eb4c17a3a/eb72e072f8ec7c899ca03591b87e9c25"
}

import {
  to = cloudflare_zone_setting.always_https
  id = "d23e1ce5ed08615e4477623eb4c17a3a/always_use_https"
}

import {
  to = cloudflare_zone_setting.min_tls
  id = "d23e1ce5ed08615e4477623eb4c17a3a/min_tls_version"
}
