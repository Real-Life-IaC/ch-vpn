import aws_cdk as cdk

from constructs_package.constants import AwsAccountId
from constructs_package.constants import AwsRegion
from constructs_package.constants import AwsStage
from infra.stack import VpnStack


app = cdk.App()

VpnStack(
    scope=app,
    id=f"Vpn-{AwsStage.SANDBOX}",
    env=cdk.Environment(account=AwsAccountId.SANDBOX, region=AwsRegion.US_EAST_1),
    cidr_block="10.112.0.0/16",
)

VpnStack(
    scope=app,
    id=f"Vpn-{AwsStage.STAGING}",
    env=cdk.Environment(account=AwsAccountId.STAGING, region=AwsRegion.US_EAST_1),
    cidr_block="10.80.0.0/16",
)

VpnStack(
    scope=app,
    id=f"Vpn-{AwsStage.PRODUCTION}",
    env=cdk.Environment(account=AwsAccountId.PRODUCTION, region=AwsRegion.US_EAST_1),
    cidr_block="10.16.0.0/16",
)

VpnStack(
    scope=app,
    id=f"Vpn-{AwsStage.MANAGEMENT}",
    env=cdk.Environment(
        account=AwsAccountId.MANAGEMENT, region=AwsRegion.US_EAST_1
    ),
    cidr_block="10.144.0.0/16",
    create_vpn=True,
)

app.synth()
