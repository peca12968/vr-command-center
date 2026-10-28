$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$checkRoot = Join-Path $projectRoot 'artifacts/unity-syntax'
New-Item -ItemType Directory -Path $checkRoot -Force | Out-Null
@'
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0</TargetFramework></PropertyGroup>
  <ItemGroup>
    <Reference Include="Microsoft.CodeAnalysis"><HintPath>$(MSBuildSDKsPath)/../Roslyn/bincore/Microsoft.CodeAnalysis.dll</HintPath></Reference>
    <Reference Include="Microsoft.CodeAnalysis.CSharp"><HintPath>$(MSBuildSDKsPath)/../Roslyn/bincore/Microsoft.CodeAnalysis.CSharp.dll</HintPath></Reference>
  </ItemGroup>
</Project>
'@ | Set-Content -LiteralPath (Join-Path $checkRoot 'UnitySyntax.csproj') -Encoding utf8NoBOM
@'
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
var files = Directory.GetFiles(args[0], "*.cs", SearchOption.AllDirectories);
var errors = files.SelectMany(file => CSharpSyntaxTree.ParseText(File.ReadAllText(file),
    new CSharpParseOptions(LanguageVersion.CSharp9), file).GetDiagnostics())
    .Where(diagnostic => diagnostic.Severity == DiagnosticSeverity.Error).ToArray();
foreach (var error in errors) Console.WriteLine(error);
Console.WriteLine($"Checked {files.Length} Unity source files with the C# 9 parser. Syntax errors: {errors.Length}.");
Console.WriteLine("This does not bind Unity SDK types, compile the Unity project, run EditMode tests or validate a headset.");
return errors.Length == 0 ? 0 : 1;
'@ | Set-Content -LiteralPath (Join-Path $checkRoot 'Program.cs') -Encoding utf8NoBOM
dotnet run --project (Join-Path $checkRoot 'UnitySyntax.csproj') --configuration Release -- (Join-Path $projectRoot 'clients/unity/Assets/VrCommand')
if ($LASTEXITCODE -ne 0) { throw 'Unity source syntax validation failed.' }
