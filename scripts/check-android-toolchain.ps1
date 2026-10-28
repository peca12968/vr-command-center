#Requires -Version 7.0
param([string]$EditorRoot = 'F:\Tools\UnityEditors\6000.3.27f1')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$androidRoot = Join-Path $EditorRoot 'Editor/Data/PlaybackEngines/AndroidPlayer'
$cmake = Join-Path $androidRoot 'SDK/cmake/3.22.1/bin/cmake.exe'
$ninja = Join-Path $androidRoot 'SDK/cmake/3.22.1/bin/ninja.exe'
$toolchain = Join-Path $androidRoot 'NDK/build/cmake/android.toolchain.cmake'
foreach ($required in @($cmake, $ninja, $toolchain)) {
    if (-not (Test-Path -LiteralPath $required)) { throw "Missing Android toolchain component: $required" }
}
$probeRoot = Join-Path $projectRoot 'artifacts/android-toolchain-check'
New-Item -ItemType Directory -Path $probeRoot -Force | Out-Null
@'
cmake_minimum_required(VERSION 3.22)
project(VrCommandAndroidProbe LANGUAGES CXX)
add_library(vr_command_probe SHARED probe.cpp)
target_compile_features(vr_command_probe PRIVATE cxx_std_17)
target_link_libraries(vr_command_probe log)
'@ | Set-Content -LiteralPath (Join-Path $probeRoot 'CMakeLists.txt') -Encoding utf8NoBOM
@'
#include <android/log.h>
#include <vector>
extern "C" __attribute__((visibility("default"))) int vr_command_probe() {
    const std::vector<int> values{1, 2, 3};
    __android_log_print(ANDROID_LOG_INFO, "VRCommand", "Android toolchain compile probe");
    return static_cast<int>(values.size());
}
'@ | Set-Content -LiteralPath (Join-Path $probeRoot 'probe.cpp') -Encoding utf8NoBOM
$output = Join-Path $probeRoot 'build'
& $cmake -S $probeRoot -B $output -G Ninja "-DCMAKE_MAKE_PROGRAM=$ninja" "-DCMAKE_TOOLCHAIN_FILE=$toolchain" -DANDROID_ABI=arm64-v8a -DANDROID_PLATFORM=android-32 -DCMAKE_BUILD_TYPE=Release
if ($LASTEXITCODE -ne 0) { throw 'Android CMake configure failed.' }
& $cmake --build $output
if ($LASTEXITCODE -ne 0) { throw 'Android native compile/link failed.' }
$library = Join-Path $output 'libvr_command_probe.so'
$bytes = [IO.File]::ReadAllBytes($library)
if ($bytes.Length -lt 20 -or $bytes[0] -ne 127 -or $bytes[1] -ne 69 -or $bytes[2] -ne 76 -or $bytes[3] -ne 70 -or $bytes[4] -ne 2 -or $bytes[5] -ne 1 -or [BitConverter]::ToUInt16($bytes, 18) -ne 183) {
    throw 'Native compiler did not produce an ELF64 AArch64 library.'
}
Write-Host "Android API 32 C++ compile/link passed: $library"
Write-Host 'This verifies the native tools, not a Unity build, APK or headset execution.'
