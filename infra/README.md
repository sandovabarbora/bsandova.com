# infra · the bsandova.com zone as code

Terraform for the Cloudflare zone: DNS placeholders, the `www → apex` redirect,
security headers on every response, HTTPS-only, TLS ≥ 1.2. The Worker that serves the
site is deployed separately by `.github/workflows/deploy.yml` from `wrangler.jsonc`.

```bash
cd infra
export CLOUDFLARE_API_TOKEN=…   # Zone: DNS Edit · Dynamic Redirect Edit · Transform Rules Edit · Zone Settings Edit
terraform init
terraform plan                  # first run: 10 imports (imports.tf), nothing recreated
terraform apply
```

State is local and ignored by git: one zone, one operator. CI checks formatting and
validity only; a plan without the state file would show every resource as new, which
is a lie, so it is not run there. Apply from a laptop, read the plan first.
