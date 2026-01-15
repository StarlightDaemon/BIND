# Troubleshooting Guide

## Installer Issues

### Script fails with "pct command not found"
- You're not on a Proxmox host
- Run this only on Proxmox VE servers

### Script fails with "must be run as root"
```bash
sudo bash install.sh
```

### Container creation fails
- Check storage is available: `pvesm status`
- Check network: `ping 8.8.8.8`

### Template download fails
```bash
pveam update  # Update template list
# Then retry installation
```

### Installation fails inside container
- Installer will offer to remove broken container
- Choose 'y' to clean up and retry

---

## Runtime Issues

### RSS feed not accessible
```bash
pct enter <container-id>
systemctl status bind-rss.service
ss -tulpn | grep 5050
curl http://localhost:5050/feed.xml
```

### No magnets collected
```bash
pct enter <container-id>
journalctl -u bind.service -n 50
ls -lh /opt/bind/magnets/
```

### Services won't start
```bash
systemctl status bind.service
systemctl status bind-rss.service
journalctl -xe
```

### Update failed / rollback needed
```bash
cd /opt/bind
git tag  # Find backup tags
git checkout backup-YYYYMMDD-HHMMSS
systemctl restart bind.service bind-rss.service
```

### Port 5050 already in use
```bash
# Find what's using it
ss -tulpn | grep 5050

# Change BIND's port (edit bind-rss.service)
# Or stop the conflicting service
```

### BiglyBT XML parsing error
Fixed in latest version (ampersands properly escaped - update to latest)
