# Break-glass access

Every login normally goes through Tailscale SSH. If Tailscale on a server stops working, use the provider's console.

1. Open the server's web or serial console. On DigitalOcean, that's **Access > Recovery Console** on the droplet.
2. Reset the root password from the provider's control panel if the console asks for one. Shipyard locks root's password at first boot.
3. Log in, then check Tailscale: `systemctl status tailscaled` and `tailscale status`.
4. If the node logged out, rejoin with a fresh single-use key from the Tailscale admin console: `tailscale up --auth-key=<key> --ssh --hostname=<project>-<env>-<name> --accept-dns=false`.
5. Lock the root password again: `passwd -l root`.

Opening port 22 to fix access is never the answer. Use the console.
