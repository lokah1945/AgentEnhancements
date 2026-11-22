<#
.SYNOPSIS
    AgentEnhancements Unified Setup — Windows PowerShell Entry Point
.DESCRIPTION
    This script is the Windows-native entry point for AgentEnhancements installation.
    It calls the shared Python installer core (installer.py) for all actual work.
    The Bash setup.sh remains the canonical entry point for Linux/macOS/WSL/Git Bash.
.NOTES
    Part of AgentEnhancements Windows Consolidation.
    Maintains CONTRACT.md §2.1 "One setup script" via shared Python core.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [string[]]$Agents,

    [Parameter(Mandatory=$false)]
    [switch]$DryRun,

    [Parameter(Mandatory=$false)]
    [switch]$Force,

    [Parameter(Mandatory=$false)]
    [switch]$SkipHooks,

    [Parameter(Mandatory=$false)]
    [switch]$SkipMcp,

    [Parameter(Mandatory=$false)]
    [switch]$SkipMemory,

    [Parameter(Mandatory=$false)]
    [switch]$SkipCompression,

    [Parameter(Mandatory=$false)]
    [switch]$SkipSkills,

    [Parameter(Mandatory=$false)]
    [switch]$Verbose,

    [Parameter(Mandatory=$false)]
    [string]$BaseDir,

    [Parameter(Mandatory=$false)]
    [switch]$DetectOnly
)

# Script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$RepoRoot = if ($BaseDir) { Resolve-Path $BaseDir } else { Resolve-Path "$ScriptDir\.." }
$InstallerPy = Join-Path $ScriptDir "scripts\installer.py"
$PythonExe = "python"

# Helper functions
function Write-Info { param([string]$Msg) Write-Host "[INFO] $Msg" -ForegroundColor Cyan }
function Write-Success { param([string]$Msg) Write-Host "[SUCCESS] $Msg" -ForegroundColor Green }
function Write-Warn { param([string]$Msg) Write-Host "[WARN] $Msg" -ForegroundColor Yellow }
function Write-ErrorMsg { param([string]$Msg) Write-Host "[ERROR] $Msg" -ForegroundColor Red }
function Write-Debug { param([string]$Msg) if ($Verbose) { Write-Host "[DEBUG] $Msg" -ForegroundColor Gray } }

# Verify Python availability
function Test-Python {
    $pythonCmds = @("python", "python3", "py -3")
    foreach ($cmd in $pythonCmds) {
        try {
            $result = & $cmd --version 2>$null
            if ($LASTEXITCODE -eq 0) {
                Write-Debug "Found Python: $cmd -> $result"
                return $cmd.Split(' ')[0]  # Return base command (handle "py -3")
            }
        } catch { }
    }
    return $null
}

# Main
Write-Info "AgentEnhancements Unified Setup (Windows PowerShell)"
Write-Info "Repo: $RepoRoot"

# Find Python
$PythonExe = Test-Python
if (-not $PythonExe) {
    Write-ErrorMsg "Python 3 not found in PATH. Please install Python 3.10+ and ensure it's in PATH."
    exit 1
}
Write-Info "Using Python: $($PythonExe --version)"

# Verify installer.py exists
if (-not (Test-Path $InstallerPy)) {
    Write-ErrorMsg "Installer core not found: $InstallerPy"
    exit 1
}

# Build arguments for installer.py
$args = @()

if ($DetectOnly) {
    $args += "detect"
} else {
    $args += "install"
}

if ($Agents) {
    $args += "--agents"
    $args += $Agents
}

if ($DryRun) { $args += "--dry-run" }
if ($Force) { $args += "--force" }
if ($SkipHooks) { $args += "--skip-hooks" }
if ($SkipMcp) { $args += "--skip-mcp" }
if ($SkipMemory) { $args += "--skip-memory" }
if ($SkipCompression) { $args += "--skip-compression" }
if ($SkipSkills) { $args += "--skip-skills" }
if ($Verbose) { $args += "--verbose" }
if ($BaseDir) { $args += "--base-dir", $RepoRoot }

Write-Debug "Running: $PythonExe $InstallerPy $($args -join ' ')"

# Execute installer
try {
    $exitCode = & $PythonExe $InstallerPy @args
    if ($exitCode -ne 0) {
        Write-ErrorMsg "Installer exited with code $exitCode"
        exit $exitCode
    }
} catch {
    Write-ErrorMsg "Failed to execute installer: $_"
    exit 1
}

Write-Success "Setup completed successfully!"

# Print next steps
if (-not $DetectOnly) {
    Write-Host ""
    Write-Host "Next steps:"
    Write-Host "  1. Restart your AI coding agent (Claude Code, Codex, etc.)"
    Write-Host "  2. Run 'python unified-integration/scripts/registry.py map \"<task>\"' to discover relevant skills"
    Write-Host "  3. Check hooks are active via agent's hook inspection (e.g., '/hooks' in Claude Code)"
    if ($Agents) {
        Write-Host "  4. Configured agents: $($Agents -join ', ')"
    }
}