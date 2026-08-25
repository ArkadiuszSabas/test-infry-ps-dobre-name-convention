# Networking Module

Creates the environment VNet, subnets reserved for Private Endpoints, Container Apps, and the
optional OpenVPN server and Private DNS zones linked to the VNet.

This module intentionally does not deploy the OpenVPN VM or ACR
private-build networking. The OpenVPN server subnet is created here so the optional OpenVPN
module can attach to the existing network shape without renumbering.

## Address Plan

The default dev address plan keeps the environment VNet at `10.42.0.0/20` and reserves:

- `10.42.0.0/24` for application service Private Endpoints;
- `10.42.2.0/24` for future OpenVPN users;
- `10.42.4.0/23` for the delegated Container Apps infrastructure subnet;
- `10.42.6.0/27` for the future OpenVPN server subnet.

Azure Container Apps requires a `/27` or larger delegated infrastructure subnet. The `/23`
default intentionally gives the environment room for multiple `/27`-sized allocations without
renumbering the VNet.

## Resources

- Environment virtual network.
- Application Private Endpoint subnet.
- Container Apps infrastructure subnet delegated to `Microsoft.App/environments`; the module
  requires at least the Azure workload-profile minimum address range.
- OpenVPN server subnet used by the optional OpenVPN module.
- Private DNS zones required by the current Private Endpoint rollout.

## Navigation

- Up: [Terraform Design](../../../docs/terraform-design.md)
