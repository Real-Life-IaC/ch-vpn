# Manual Deployment Steps

## Generating the VPN certificate

We must generate a certificate for encrypted communication between the client VPN software and the client VPN endpoint.

```bash
# Clone easy-rsa repo from GitHub.
git clone https://github.com/OpenVPN/easy-rsa.git

# Generate the certificate.
# When prompted for information, use the default values.
cd easy-rsa/easyrsa3
./easyrsa init-pki
./easyrsa build-ca nopass
./easyrsa build-server-full server nopass
./easyrsa build-client-full client1.domain.tld nopass

# Copy the certificate files to a new directory.
mkdir -p aws_client_vpn_files
cp pki/ca.crt aws_client_vpn_files/
cp pki/issued/server.crt aws_client_vpn_files/
cp pki/private/server.key aws_client_vpn_files/
cp pki/issued/client1.domain.tld.crt aws_client_vpn_files/
cp pki/private/client1.domain.tld.key aws_client_vpn_files/

# List files in the new directory
ls -l aws_client_vpn_files/
```

Then import the certificate to AWS Certificate manager:

* Certificate: `server.crt`
* Key: `server.key`
* Chain: `ca.crt`
