param(
    [Parameter(Mandatory)][string]$Directory,
    [Parameter(Mandatory)][string]$Address
)

$ErrorActionPreference = 'Stop'
$password = $env:VR_COMMAND_CONTROL_PFX_PASSWORD
if ([string]::IsNullOrEmpty($password)) { throw 'Missing fixture PFX password.' }
$from = [DateTimeOffset]::UtcNow.AddMinutes(-5)
$hash = [System.Security.Cryptography.HashAlgorithmName]::SHA256
$padding = [System.Security.Cryptography.RSASignaturePadding]::Pkcs1
$rootKey = [System.Security.Cryptography.RSA]::Create(2048)
$issuerKey = [System.Security.Cryptography.RSA]::Create(2048)
$leafKey = [System.Security.Cryptography.RSA]::Create(2048)

try {
    $rootRequest = [System.Security.Cryptography.X509Certificates.CertificateRequest]::new('CN=VR HTTPS Fixture Root', $rootKey, $hash, $padding)
    $rootRequest.CertificateExtensions.Add([System.Security.Cryptography.X509Certificates.X509BasicConstraintsExtension]::new($true, $true, 1, $true))
    $root = $rootRequest.CreateSelfSigned($from, $from.AddDays(3))

    $issuerRequest = [System.Security.Cryptography.X509Certificates.CertificateRequest]::new('CN=VR HTTPS Fixture Issuer', $issuerKey, $hash, $padding)
    $issuerRequest.CertificateExtensions.Add([System.Security.Cryptography.X509Certificates.X509BasicConstraintsExtension]::new($true, $true, 0, $true))
    $issuerPublic = $issuerRequest.Create($root, $from, $from.AddDays(2), [byte[]]@(2))
    $issuer = [System.Security.Cryptography.X509Certificates.RSACertificateExtensions]::CopyWithPrivateKey($issuerPublic, $issuerKey)

    $leafRequest = [System.Security.Cryptography.X509Certificates.CertificateRequest]::new('CN=VR HTTPS Fixture Site', $leafKey, $hash, $padding)
    $leafRequest.CertificateExtensions.Add([System.Security.Cryptography.X509Certificates.X509BasicConstraintsExtension]::new($false, $false, 0, $true))
    $san = [System.Security.Cryptography.X509Certificates.SubjectAlternativeNameBuilder]::new()
    $san.AddIpAddress([System.Net.IPAddress]::Parse($Address))
    $leafRequest.CertificateExtensions.Add($san.Build())
    $leafPublic = $leafRequest.Create($issuer, $from, $from.AddDays(1), [byte[]]@(3))
    $leaf = [System.Security.Cryptography.X509Certificates.RSACertificateExtensions]::CopyWithPrivateKey($leafPublic, $leafKey)

    $certificates = [System.Security.Cryptography.X509Certificates.X509Certificate2Collection]::new()
    [void]$certificates.Add($leaf)
    [void]$certificates.Add($issuerPublic)
    [IO.File]::WriteAllBytes((Join-Path $Directory 'control-https.pfx'), $certificates.Export('Pkcs12', $password))
    [IO.File]::WriteAllBytes((Join-Path $Directory 'leaf.cer'), $leafPublic.RawData)
    [IO.File]::WriteAllText((Join-Path $Directory 'root.pem'), $root.ExportCertificatePem())
} finally {
    foreach ($item in @($leaf, $leafPublic, $issuer, $issuerPublic, $root, $leafKey, $issuerKey, $rootKey)) {
        if ($null -ne $item) { $item.Dispose() }
    }
}
