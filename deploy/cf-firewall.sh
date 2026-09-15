#!/bin/bash
# Tighten 80/443 to Cloudflare origins only. Run AFTER CF is verified serving.
# SSH (22) stays open to the world. To roll back: delete the two deny lines
# from /etc/ufw/before.rules and `ufw reload`.
set -e
for ip in 173.245.48.0/20 103.21.244.0/22 103.22.200.0/22 103.31.4.0/22 141.101.64.0/18 108.162.192.0/18 190.93.240.0/20 188.114.96.0/20 197.234.240.0/22 198.41.128.0/17 162.158.0.0/15 104.16.0.0/13 104.24.0.0/14 172.64.0.0/13 131.0.72.0/22; do
  ufw allow from "$ip" to any port 80,443 proto tcp >/dev/null
done
python3 - << 'PYEOF'
p = "/etc/ufw/before.rules"
t = open(p).read()
anchor = "-A ufw-before-input -i lo -j ACCEPT"
deny = "-A ufw-before-input -p tcp -m multiport --dports 80,443 -j DROP"
if deny not in t:
    t = t.replace(anchor, anchor + "\n" + deny, 1)
    open(p, "w").write(t)
    print("deny rule added")
else:
    print("deny rule already present")
PYEOF
ufw reload
ufw status | head -25
