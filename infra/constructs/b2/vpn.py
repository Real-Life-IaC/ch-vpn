import aws_cdk as cdk

from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_ssm as ssm
from constructs import Construct
from infra.constructs.l2.transit_gateway import L2TransitGateway, L2TransitGatewayAttachment, L2TransitGatewayAttachmentRoutes


class B2Vpn(Construct):
    """Create a Client VPN"""

    def __init__(
        self,
        scope: Construct,
        id: str,
        vpc: ec2.Vpc,
        cidr_block: str,
    ) -> None:
        super().__init__(scope, id)

        # The CIDR block of the VPC that contains the VPN
        self.cidr_block = cidr_block

        # Client VPN SAML provider
        client_vpn_saml_provider = iam.SamlProvider(
            scope=self,
            id="ClientVpnProvider",
            metadata_document=iam.SamlMetadataDocument.from_file(
                "./infra/constructs/b2/saml/client_vpn.xml"
            ),
        )

        # VPN Self Service Portal SAML provider
        vpn_self_service_saml_provider = iam.SamlProvider(
            scope=self,
            id="VpnSelfServiceProvider",
            metadata_document=iam.SamlMetadataDocument.from_file(
                "./infra/constructs/b2/saml/vpn_self_service.xml"
            ),
        )

        # VPN Security Group
        security_group = ec2.SecurityGroup(
            scope=self,
            id="SecurityGroup",
            vpc=vpc,
            allow_all_outbound=True,
            description="VPN Security Group",
        )
        cdk.Tags.of(security_group).add(key="Name", value="VPN Security Group")

        # Client VPN
        self.client_vpn = vpc.add_client_vpn_endpoint(
            id="ClientVpn",
            description="VPN Client to access private resources",
            # IP range that will be allocated to the VPN clients
            # It shouldn't overlap the VPCs or a network that the client device is connected to
            cidr="192.168.0.0/18",
            # Certificate manually imported into management account. See README.md
            server_certificate_arn="arn:aws:acm:us-east-1:267631547124:certificate/c7268850-7298-417e-8f13-193f6d1d318a",
            self_service_portal=True,
            authorize_all_users_to_vpc_cidr=False,
            user_based_authentication=ec2.ClientVpnUserBasedAuthentication.federated(
                saml_provider=client_vpn_saml_provider,
                self_service_saml_provider=vpn_self_service_saml_provider,
            ),
            split_tunnel=True,
            session_timeout=ec2.ClientVpnSessionTimeout.TEN_HOURS,
            security_groups=[security_group],
            vpc_subnets=ec2.SubnetSelection(subnet_group_name="VpnSubnet"),
            client_login_banner="This VPN connection expires in 10 hours.",
            dns_servers=[self.dns_server], # Look at the property below
        )

        cdk.Tags.of(self.client_vpn).add(key="Name", value="Client VPN")

        # Allow the VPN SSO group to connect to the VPN
        self.client_vpn.add_authorization_rule(
            id="AllowVpnAccess",
            description="Allow access to all VPCs",
            cidr="10.0.0.0/8",
            # The VPN group that we created manually in the IAM Identity Center console
            group_id="24c81478-10c1-7047-9b7c-e886da56f09e",
        )

        # Add a route to for each VPN subnet in the VPC
        subnets = vpc.select_subnets(subnet_group_name="VpnSubnet").subnets
        for subnet in subnets:
            self.client_vpn.add_route(
                id=f"VpnRoute{subnet.node.id}",
                cidr="10.0.0.0/8",
                target=ec2.ClientVpnRouteTarget.subnet(subnet=subnet),
            )

        cdk.Tags.of(self).add(key="service-name", value="vpn")

    @property
    def dns_server(self) -> str:
        """The Route53 resolver IP address is on x.x.x.2"""

        # Removes the mask from the CIDR block
        ip_address = self.cidr_block.split("/")[0]
        # Get the octets of the IP address
        octets = ip_address.split(".")
        # The Route53 resolver IP address is on x.x.x.2
        return ".".join(octets[:3]) + ".2"


class B2SharedTgw(Construct):
    """Transit Gateway Construct"""

    def __init__(self, scope: Construct, id: str) -> None:
        super().__init__(scope, id)

        organization_arn = ssm.StringParameter.value_for_string_parameter(
            scope=self,
            parameter_name="/platform/orgs/organization/arn",
        )

        # Create the transit gateway
        self.transit_gateway = L2TransitGateway(
            scope=self,
            id="TransitGateway",
            description="Allow connection to all other accounts in the Organization",
        )

        # Allow all accounts in the organization to attach
        # to the transit gateway in the management account
        self.transit_gateway.create_resource_share(
            principals=[organization_arn],
        )


class B2SharedTgwAttachment(Construct):
    """Transit Gateway Attachment Construct"""

    def __init__(
        self,
        scope: Construct,
        id: str,
        vpc: ec2.Vpc,
        subnets: list[ec2.Subnet],
        transit_gateway: L2TransitGateway | None = None,
    ) -> None:
        super().__init__(scope, id)

        stage = ssm.StringParameter.value_from_lookup(
            scope=self,
            parameter_name="/platform/stage",
        )

        if transit_gateway:
            transit_gateway_id = transit_gateway.transit_gateway_id
        else:
            transit_gateway_id = ssm.StringParameter.value_from_lookup(
                scope=self,
                parameter_name="/platform/vpn/transit-gateway/id",
            )

        # Do not create the attachment if the transit gateway id is not set
        # need to create the parameter manually in all accounts with a dummy value
        # Then after the transit gateway is created, update the parameter with the correct value
        if not transit_gateway_id.startswith("dummy-value-for-"):
            tgw_attachment = L2TransitGatewayAttachment(
                scope=self,
                id="TransitGatewayAttachment",
                vpc=vpc,
                stage=stage,
                transit_gateway_id=transit_gateway_id,
            )

            L2TransitGatewayAttachmentRoutes(
                scope=self,
                id="TransitGatewayAttachmentRoutes",
                transit_gateway_attachment=tgw_attachment,
                destination_cidr_block="10.0.0.0/8",
                subnets=subnets,
            )
