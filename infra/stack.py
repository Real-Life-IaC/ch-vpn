import aws_cdk as cdk

from constructs import Construct
from infra.constructs.b2.vpn import B2Vpn, B2SharedTgwAttachment, B2SharedTgw
from aws_cdk import aws_ssm as ssm
from aws_cdk import aws_ec2 as ec2

class VpnStack(cdk.Stack):
    """Create the VPN"""

    def __init__(
        self,
        scope: Construct,
        id: str,
        cidr_block: str,
        create_vpn: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        vpc = ec2.Vpc.from_lookup(
            scope=self,
            id="Vpc",
            vpc_id=ssm.StringParameter.value_from_lookup(
                scope=self,
                parameter_name="/platform/vpc/id",
            ),
        )

        # We only create the VPN in the management account
        if create_vpn:
            B2Vpn(
                scope=self,
                id="Vpn",
                vpc=vpc,
                cidr_block=cidr_block,
            )

            shared_tgw = B2SharedTgw(
                scope=self,
                id="SharedTgw",
            )

            # Attach Transit Gateway to the VPN subnet
            B2SharedTgwAttachment(
                scope=self,
                id="VpnSubnetTgwAttachment",
                vpc=vpc,
                subnets=vpc.select_subnets(subnet_group_name="VpnSubnet").subnets,
                transit_gateway=shared_tgw.transit_gateway,
            )
        # In the other accounts we use the shared transit gateway to connect to the VPN
        else:
            # Attach Transit Gateway to the Private Subnet in all stages except management
            B2SharedTgwAttachment(
                scope=self,
                id="PrivateSubnetTgwAttachment",
                vpc=vpc,
                subnets=vpc.select_subnets(subnet_group_name="PrivateSubnet").subnets,
            )

        ssm.StringParameter(
            scope=self,
            id="TransitGatewayCidrBlock",
            # WARNING: Hardcoded to include the VPN subnet CIDR block
            # Copied it from the AWS console
            # /24 to include all subnets in the 10.144.140.x range
            string_value="10.144.140.0/24",
            description="Transit Gateway Cidr Block - VPN",
            parameter_name="/platform/vpn/transit-gateway/cidr-block",
        )


        # Add tags to everything in this stack
        cdk.Tags.of(self).add(key="owner", value="Platform")
        cdk.Tags.of(self).add(key="repo", value="ch-platform")
        cdk.Tags.of(self).add(key="stack", value=self.stack_name)
