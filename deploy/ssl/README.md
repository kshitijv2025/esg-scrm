# SSL Certificates

Production TLS certificates go here.

## Option 1: Let's Encrypt (recommended)

```bash
certbot --nginx -d yourdomain.com
# Copy resulting certs:
#   /etc/letsencrypt/live/yourdomain.com/fullchain.pem → ./fullchain.pem
#   /etc/letsencrypt/live/yourdomain.com/privkey.pem   → ./privkey.pem
```

## Option 2: Self-signed (development only)

```bash
openssl req -x509 -nodes -days 365 \
  -newkey rsa:2048 \
  -keyout privkey.pem \
  -out fullchain.pem \
  -subj "/CN=localhost/O=ESG SCRM Dev"
```

## Option 3: Cloud-managed certificates (AWS ACM, GCP Cloud DNS, etc.)

Download the certificate chain and private key, then place:

- `fullchain.pem` — certificate + intermediates
- `privkey.pem` — private key (chmod 600)

## Production checklist

- [ ] Uncomment the HTTPS `server` block in `nginx.conf`
- [ ] Point `ssl_certificate` to `/etc/nginx/ssl/fullchain.pem`
- [ ] Point `ssl_certificate_key` to `/etc/nginx/ssl/privkey.pem`
- [ ] Redirect HTTP → HTTPS (add a port 80 server block with `return 301 https://$host$request_uri`)
- [ ] Set `HSTS` header (uncomment the `Strict-Transport-Security` line)
