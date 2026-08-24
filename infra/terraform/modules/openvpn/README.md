# OpenVPN Module

Creates the optional OpenVPN server bootstrap for one DocMind.ai environment.

## Scope

- Static Standard public IP address.
- Network Security Group with UDP OpenVPN ingress on the configured port.
- Mandatory administrative SSH ingress for an active VM on a managed high port, only from explicit trusted CIDR
  ranges.
- VM extension hardening for SSH passwordless key-only access and named operator public keys.
- Explicit intra-VNet inbound deny to avoid relying on Azure NSG default allow rules.
- Linux VM using `Standard_B2ts_v2` by default.
- User-assigned managed identity attached to the VM.
- OpenVPN Community Edition bootstrap through cloud-init.
- DNS forwarding through `dnsmasq` to Azure-provided DNS for Private Endpoint name resolution.
- Dedicated OpenVPN runtime Key Vault synchronization at boot and on a cron interval.

Terraform does not store CA private keys, server private keys, client private keys, or client
profiles. SSH operators use `docmind-openvpn-profile` for client profile generation,
download, revocation, and CA rotation outside Terraform state. Generated profile payloads
are stored in the operator-only CA Key Vault, not in the runtime vault read by the VM. CA
rotation publishes a runtime bundle with both PKI and matching client-registry data, promotes
the same PKI and registry to standalone runtime secrets, and stores a generation-specific CA key
secret so the VM sync job does not read a partially updated CA/server certificate set or revive
stale state if the bundle is missing. The bundle is the cutover marker and is written before
standalone fallback promotion. During an explicit bootstrap
window, when the OpenVPN server PKI secrets are missing,
the VM creates the bootstrap CA, server certificate, Diffie-Hellman parameters, `tls-crypt`
key, and an empty active-client registry, then writes runtime values to the OpenVPN runtime Key
Vault and the CA private key to a separate operator-only CA Key Vault through its managed
identity.
The root module should grant that managed identity temporary `Key Vault Secrets Officer`
read-write secret access only during the bootstrap window controlled by
`openvpn_vm_secret_bootstrap_enabled`, and only to the dedicated OpenVPN vaults, not to the
environment application Key Vault. Remove that temporary role immediately after bootstrap.
After bootstrap, the VM keeps runtime read access only to the OpenVPN runtime Key Vault and
does not retain read access to the CA Key Vault.

## Access Model

The module currently defines one `private` access profile. It pushes only the CIDRs passed in
`private_access_cidrs`, which the root module wires to the application Private Endpoint
subnet. Client entries in Key Vault cannot override the pushed route list; the
SSH profile operations may update the Key Vault client registry and add or revoke profiles without
changing the VNet address plan. Generated profiles derive the VPN DNS forwarder from the first
usable client-CIDR address and use client-native split-DNS directives for the Azure service
namespaces backed by the routed Private Endpoints. They use `ignore-unknown-option dns` so older
clients can ignore unsupported native DNS directives and retain the server-pushed DNS fallback;
OpenVPN 2.6+ recognizes the syntax, but split-DNS behavior requires a client and platform that
also implement `resolve-domains`.
Azure Monitor coverage includes the Application Insights query API under
`applicationinsights.io`, both the legacy `loganalytics.io` and current
`loganalytics.azure.com` Log Analytics query APIs, and the ingestion and shared endpoint
namespaces represented by the AMPLS Private DNS zones.

The VM enforces active client common names through an OpenVPN `client-connect` hook. With the
default empty client registry, no user profile can connect until an SSH operator creates
client certificates and updates the registry. A separate `tls-verify` hook validates the
client certificate SHA256 fingerprint from the registry, so reissuing a profile for the same
common name stops older downloaded profiles after the sync job reloads state.

Administrative SSH is configured after VM creation through a Custom Script Extension so
operator-key rotation does not require replacing the VM. When the active VM has SSH source
prefixes, the extension disables password,
keyboard-interactive, root, TCP forwarding, and X11 access; writes only named operator
`ssh-ed25519` public keys to `authorized_keys`; and installs the `docmind-openvpn-profile`
wrapper used by SSH operators. Disabling the OpenVPN VM removes the VM and SSH together; PKI
can remain independently enabled. The VM bootstrap admin key is used for Azure VM
provisioning, but it is not kept in the extension-managed direct-operator key set after SSH
hardening runs. Generated `.ovpn` profiles are not staged as files on the VM; direct operators
download them from the operator-only CA Key Vault through the wrapper's `download-profile`
subcommand over SSH stdout.

The same extension converges the OpenVPN systemd dependency drop-in before updating
`server.json`. The OpenVPN unit requires the boot-time `docmind-openvpn-sync.service`, but does
not invoke the mutating sync script through `ExecStartPre`; runtime convergence runs the sync
outside the OpenVPN unit's protected filesystem context and avoids a recursive service restart.

If Key Vault sync or client-registry validation fails, the VM clears the rendered client
allowlist, rewrites firewall rules to deny VPN forwarding, and stops OpenVPN instead of using
stale access state.

## Out Of Scope

- Azure Container Registry private-only build or push path.
- Client certificate generation in Terraform.
- Container Apps Environment private-only access cutover.

## Navigation

- Up: [Terraform Design](../../../docs/terraform-design.md)
- Up: [Infrastructure Documentation](../../../docs/INDEX.md)
