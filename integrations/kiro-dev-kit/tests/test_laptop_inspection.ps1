$ErrorActionPreference = 'Stop'
$script = Join-Path (Split-Path -Parent $PSScriptRoot) 'scripts/Inspect-KiroLaptop.ps1'
$tokens=$null; $errors=$null
$ast=[System.Management.Automation.Language.Parser]::ParseFile($script,[ref]$tokens,[ref]$errors)
if ($errors.Count) { throw 'Laptop inspection script does not parse' }
# Enforce the small set of metadata commands and no dynamic invocation.
$allowed=@('Get-CimInstance','Get-Command','Test-Path','Get-ExecutionPolicy','Select-Object','Get-ItemProperty','ConvertTo-Json')
$commands=$ast.FindAll({param($node) $node -is [System.Management.Automation.Language.CommandAst]},$true)
foreach($command in $commands) {
    if($command.GetCommandName() -notin $allowed) { throw 'Inspection contains an unexpected command' }
}
$writes=$ast.FindAll({param($node) $node -is [System.Management.Automation.Language.RedirectionAst] -or $node -is [System.Management.Automation.Language.InvokeMemberExpressionAst]},$true)
if($writes.Count) { throw 'Inspection contains redirection or method invocation' }

# Simulate a locked-down laptop. No applications or real policy queries run.
function Get-CimInstance { [CmdletBinding()] param($ClassName,$Property) throw 'private-system-sentinel' }
function Get-Command { [CmdletBinding()] param($Name,$CommandType) }
function Test-Path { [CmdletBinding()] param($LiteralPath,$PathType) return $false }
function Get-ExecutionPolicy { [CmdletBinding()] param([switch]$List) throw 'private-policy-sentinel' }
function Get-ItemProperty { [CmdletBinding()] param($LiteralPath,$Name) throw 'private-registry-sentinel' }
$text=(& $script | Out-String)
$report=$text | ConvertFrom-Json
if($report.installation_allowed -ne 'NOT_DETERMINED' -or $report.os.status -ne 'UNKNOWN_OR_NOT_READABLE') { throw 'Unreadable state was treated as permission' }
if($report.applications_started -ne 0 -or -not $report.read_only) { throw 'Unexpected inspection action' }
if($text -match 'private-.*-sentinel') { throw 'Private error details escaped inspection' }
Write-Host 'PASS: metadata command boundary and unreadable-policy reporting.'
