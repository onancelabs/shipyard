# Recover a failed Tailscale join

`make configure` waits five minutes for each server to answer over Tailscale. If a server never answers, check these in order.

1. **Is your machine on the tailnet?** Run `tailscale status`. `make check` catches this before provisioning starts.
2. **Did the server appear in the Tailscale admin console?** If it did, but under a different name (such as `<name>-1`), an old machine still holds the name. Remove the old machine and rename the new one.
3. **Is the server tagged correctly?** The ACL must allow your account or CI tag to reach `tag:<project>-<env>`. See [tailscale-acl.hujson](../tailscale-acl.hujson).
4. **Did first boot finish?** Open the provider's console and read `/var/log/cloud-init-output.log`. A slow boot can outlast the 30-minute key.

First-boot setup runs only once, when the server is created. Editing it later does nothing for an existing server. If the join failed, rebuild the server. See [Rebuild a server](rebuild-a-server.md). It's quicker than repairing the boot by hand.
