# Manual Deployment Steps

## Generating the VPN certificate

We must generate a certificate for encrypted communication between the client VPN software and the client VPN endpoint.

```bash
# Clone easy-rsa repo from GitHub.
export EASYRSA_BATCH=1
git clone https://github.com/OpenVPN/easy-rsa.git

# Generate the certificate.
# When prompted for information, use the default values.
cd easy-rsa/easyrsa3
./easyrsa init-pki
./easyrsa build-ca nopass
./easyrsa --san=DNS:server build-server-full server nopass
./easyrsa build-client-full client1.domain.tld nopass

# Copy the certificate files to a new directory.
mkdir -p aws_client_vpn_files
cp pki/ca.crt aws_client_vpn_files/
cp pki/issued/server.crt aws_client_vpn_files/
cp pki/private/server.key aws_client_vpn_files/
cp pki/issued/client1.domain.tld.crt aws_client_vpn_files/
cp pki/private/client1.domain.tld.key aws_client_vpn_files/

# Import the certificate to AWS Certificate Manager.
aws sso login
cd aws_client_vpn_files/
aws acm import-certificate --certificate fileb://server.crt --private-key fileb://server.key --certificate-chain fileb://ca.crt --profile management_admin
```

## Connect Root Account VPC to hosted zones in other accounts

Unfortunately, this setup requires another manual step to enable DNS resolution. We need to associate the private hosted zones from each account with the VPC from which the VPN traffic comes. In our case, associate each Private Hosted Zone with the Management Account VPC.

**See the official AWS docs here: [Associating an Amazon VPC and a private hosted zone that you created with different AWS accounts](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/hosted-zone-private-associate-vpcs-different-accounts.html)**

Below are the commands to execute with AWS CLI (It's not possible to do this operation in the console):

```bash
aws route53 create-vpc-association-authorization --hosted-zone-id "<hosted-zone-id-from-child-account>" --vpc "VPCRegion=us-east-1,VPCId=<vpc-id-from-management-account>" --profile <child-account-profile>

aws route53 associate-vpc-with-hosted-zone --hosted-zone-id "<hosted-zone-id-from-child-account>" --vpc "VPCRegion=us-east-1,VPCId=<vpc-id-from-management-account>" --profile <management-account-profile>
```
