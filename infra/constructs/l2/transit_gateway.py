import aws_cdk as cdk
import aws_cdk.aws_ram as ram

from aws_cdk import aws_ec2 as ec2
from constructs import Construct


class L2TransitGateway(ec2.CfnTransitGateway):
    """Transit Gateway L2 Construct"""

    def __init__(
        self,
        scope: Construct,
        id: str,
        description: str | None = None,
        amazon_side_asn: int = 64512,
        auto_accept_shared_attachments: bool = True,
        default_route_table_association: bool = True,
        default_route_table_propagation: bool = True,
        dns_support: bool = True,
        multicast_support: bool = False,
        vpn_ecmp_support: bool = False,
    ) -> None:
        self.id = id
        bools = ("disable", "enable")

        super().__init__(
            scope=scope,
            id=self.id,
            amazon_side_asn=amazon_side_asn,
            auto_accept_shared_attachments=bools[auto_accept_shared_attachments],
            default_route_table_association=bools[default_route_table_association],
            default_route_table_propagation=bools[default_route_table_propagation],
            description=description,
            dns_support=bools[dns_support],
            multicast_support=bools[multicast_support],
            vpn_ecmp_support=bools[vpn_ecmp_support],
        )

    @property
    def transit_gateway_id(self) -> str:
        """Return the transit gateway id"""
        return self.attr_id

    @property
    def transit_gateway_arn(self) -> str:
        """Return the transit gateway arn"""
        return self.attr_transit_gateway_arn

    def create_resource_share(
        self,
        principals: list[str],
        allow_external_principals: bool = False,
    ) -> ram.CfnResourceShare:
        """Create a resource share for the transit gateway

        :param principals_arns: Specifies the principals to associate
        with the resource share. The possible values are:
            - An AWS account ID
            - An ARN of an organization in AWS Organizations
            - An ARN of an organizational unit (OU) in AWS Organizations
            - An ARN of an IAM role
            - An ARN of an IAM user
        """

        return ram.CfnResourceShare(
            scope=self,
            id=f"{self.id}ResourceShare",
            name=f"{self.id}ResourceShare",
            allow_external_principals=allow_external_principals,
            resource_arns=[self.transit_gateway_arn],
            principals=principals,
        )


class L2TransitGatewayAttachment(ec2.CfnTransitGatewayAttachment):
    """Transit Gateway Attachment L2 Construct"""

    def __init__(
        self,
        scope: Construct,
        id: str,
        vpc: ec2.Vpc,
        stage: str,
        transit_gateway_id: str,
    ) -> None:
        super().__init__(
            scope=scope,
            id=id,
            subnet_ids=vpc.select_subnets(subnet_group_name="VpnSubnet").subnet_ids,
            vpc_id=vpc.vpc_id,
            transit_gateway_id=transit_gateway_id,
            tags=[
                cdk.CfnTag(key="Name", value=f"{stage}-Attachment"),
            ],
        )


class L2TransitGatewayAttachmentRoutes(Construct):
    """Transit Gateway Attachment Routes L2 Construct"""

    def __init__(
        self,
        scope: Construct,
        id: str,
        transit_gateway_attachment: L2TransitGatewayAttachment,
        destination_cidr_block: str,
        subnets: list[ec2.Subnet],
    ) -> None:
        super().__init__(scope, id)

        self.node.add_dependency(transit_gateway_attachment)

        for idx, subnet in enumerate(subnets):
            ec2.CfnRoute(
                scope=self,
                id=f"TgwRoute{idx}",
                route_table_id=subnet.route_table.route_table_id,
                destination_cidr_block=destination_cidr_block,
                transit_gateway_id=transit_gateway_attachment.transit_gateway_id,
            )
