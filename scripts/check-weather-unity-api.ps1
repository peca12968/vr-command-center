param([string]$EditorDirectory = 'F:\Tools\UnityEditors\6000.3.27f1\Editor')
$ErrorActionPreference = 'Stop'
$weatherRoot = Split-Path -Parent $PSScriptRoot
$weatherCheck = Join-Path $weatherRoot 'artifacts/weather-unity-api'
$weatherManaged = Join-Path $EditorDirectory 'Data/Managed/UnityEngine'
foreach ($weatherModule in @('UnityEngine.CoreModule.dll', 'UnityEngine.AudioModule.dll')) {
    if (-not (Test-Path -LiteralPath (Join-Path $weatherManaged $weatherModule))) { throw "Missing actual Unity SDK module: $weatherModule" }
}
New-Item -ItemType Directory -Path $weatherCheck -Force | Out-Null
$weatherProject = @"
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup><TargetFramework>netstandard2.1</TargetFramework><LangVersion>9.0</LangVersion><Nullable>disable</Nullable><ImplicitUsings>disable</ImplicitUsings><EnableDefaultCompileItems>false</EnableDefaultCompileItems><RestorePackagesWithLockFile>false</RestorePackagesWithLockFile></PropertyGroup>
  <ItemGroup>
    <ProjectReference Include="$weatherRoot/src/VrCommand.Simulation/VrCommand.Simulation.csproj" />
    <Compile Include="$weatherRoot/clients/unity/Assets/VrCommand/Runtime/UnityWeatherView.cs" />
    <Reference Include="UnityEngine.CoreModule"><HintPath>$weatherManaged/UnityEngine.CoreModule.dll</HintPath><Private>false</Private></Reference>
    <Reference Include="UnityEngine.AudioModule"><HintPath>$weatherManaged/UnityEngine.AudioModule.dll</HintPath><Private>false</Private></Reference>
  </ItemGroup>
</Project>
"@
[IO.File]::WriteAllText((Join-Path $weatherCheck 'WeatherApi.csproj'), $weatherProject, [Text.UTF8Encoding]::new($false))
dotnet build (Join-Path $weatherCheck 'WeatherApi.csproj') --configuration Release --artifacts-path (Join-Path $weatherCheck 'build')
if ($LASTEXITCODE -ne 0) { throw 'Weather renderer did not bind to actual Unity SDK types.' }
Write-Host 'UnityWeatherView binds to actual installed Unity Core/Audio modules. This is not a Unity project build, NGO/ILPP execution, shader/audio import, EditMode test, APK or headset result.'
