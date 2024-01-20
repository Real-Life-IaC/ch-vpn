import aws_cdk as cdk

from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_ssm as ssm
from constructs import Construct
from infra.constructs.l2.transit_gateway import TransitGateway
from infra.constructs.l2.transit_gateway import TransitGatewayAttachment


class B2Vpn(Construct):
    """Create a Client VPN"""

    def __init__(
        self,
        scope: Construct,
        id: str,
        vpc: ec2.Vpc,
    ) -> None:
        super().__init__(scope, id)

        # Certificate manually imported into management account # TODO: reimport the cert
        certificate_arn = "arn:aws:acm:us-east-1:767397808306:certificate/c2a3aae7-3d93-4fd2-836e-4e0158a7f1c4"  # noqa: B950
        # IP range that will be allocated to the VPN clients
        # It shouldn't overlap the VPCs or a network that the client device is connected to
        vpn_cidr_block = "192.168.0.0/18"
        # The CIDR block that contains the VPCs we want to access
        network_cidr_block = "10.0.0.0/8"
        # The VPN group that we created manually in the IAM Identity Center console
        vpn_sso_group_id = "24c81478-10c1-7047-9b7c-e886da56f09e"

        # Client VPN SAML provider
        client_vpn_saml_provider = iam.SamlProvider(
            scope=self,
            id="ClientVpnProvider",
            metadata_document=iam.SamlMetadataDocument.from_file(
                "./infra/constructs/b1/saml/client_vpn.xml"
            ),
        )

        # VPN Self Service Portal SAML provider
        vpn_self_service_saml_provider = iam.SamlProvider(
            scope=self,
            id="VpnSelfServiceProvider",
            metadata_document=iam.SamlMetadataDocument.from_file(
                "./infra/constructs/b1/saml/vpn_self_service.xml"
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
        cdk.Tags.of(security_group).add(
            key="Name", value="VPN Security Group"
        )

        # Client VPN
        self.client_vpn = vpc.add_client_vpn_endpoint(
            id="ClientVpn",
            description="VPN Client to access util resources",
            cidr=vpn_cidr_block,
            server_certificate_arn=certificate_arn,
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
            dns_servers=["10.100.0.2"],
        )

        # Allow the VPN SSO group to connect to the VPN
        self.client_vpn.add_authorization_rule(
            id="AllowAllVpcAccess",
            description="Allow access to all VPCs",
            cidr=network_cidr_block,
            group_id=vpn_sso_group_id,
        )

        # Add a route to for each VPN subnet in the VPC
        subnets = vpc.select_subnets(subnet_group_name="VpnSubnet").subnets
        for subnet in subnets:
            self.client_vpn.add_route(
                id=f"SubnetVpnRoute{subnet.node.id}",
                cidr=network_cidr_block,
                target=ec2.ClientVpnRouteTarget.subnet(subnet=subnet),
            )


class B2TransitGateway(Construct):
    """Transit Gateway Construct"""

    def __init__(self, scope: Construct, id: str) -> None:
        super().__init__(scope, id)

        # Create the transit gateway
        self.transit_gateway = TransitGateway(
            scope=self,
            id="TransitGateway",
            description="Allow connection to all other accounts in the Organization",
        )

        # Allow all accounts in the organization to attach
        # to the transit gateway in the management account
        # Get the organization ID (last part of the ARN)
        # from your management account's console
        self.transit_gateway.create_resource_share(
            principals=[
                f"arn:aws:organizations::{cdk.Aws.ACCOUNT_ID}:organization/o-xx8ylcz0i0"
            ],
        )

        # Create a SSM parameter for the transit gateway ARN
        ssm.StringParameter(
            scope=self,
            id="TransitGatewayArn",
            string_value=self.transit_gateway.transit_gateway_arn,
            description="Transit Gateway ARN",
            parameter_name="/platform/vpn/transit-gateway/arn",
        )


class B2TransitGatewayAttachment(Construct):
    """Transit Gateway Attachment Construct"""

    def __init__(
        self,
        scope: Construct,
        id: str,
        vpc: ec2.Vpc,
        transit_gateway_id: str,
    ) -> None:
        super().__init__(scope, id)

        TransitGatewayAttachment(
            scope=self,
            id="TransitGatewayAttachment",
            subnets=vpc.select_subnets(subnet_group_name="VpnSubnet"),
            vpc=vpc,
            transit_gateway_id=transit_gateway_id,
        )
