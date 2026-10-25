#requires -Version 7.2
[CmdletBinding()]
param([Parameter(Mandatory)][string]$WorkRoot)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
if (-not [IO.Path]::IsPathFullyQualified($WorkRoot) -or [IO.File]::Exists($WorkRoot) -or [IO.Directory]::Exists($WorkRoot)) { throw 'WorkRoot must be a new absolute directory outside the source checkout.' }
$moduleRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$fullWork=[IO.Path]::GetFullPath($WorkRoot)
if ($fullWork.StartsWith($moduleRoot,[StringComparison]::OrdinalIgnoreCase)) {throw 'WorkRoot must be outside the module.'}
[void][IO.Directory]::CreateDirectory($fullWork)
$tool=Join-Path $moduleRoot 'Test-ZipPackagePolicy.ps1'
$script:count=0
function Assert($Condition,[string]$Message) {if (-not $Condition) {throw $Message}}
function Make-Zip([string]$Name,[object[]]$Entries) {
    $path=Join-Path $fullWork ($Name+'.zip');$stream=[IO.File]::Open($path,[IO.FileMode]::CreateNew)
    $zip=[IO.Compression.ZipArchive]::new($stream,[IO.Compression.ZipArchiveMode]::Create,$false)
    try {foreach($spec in $Entries){$entry=$zip.CreateEntry($spec.name);if($spec.ContainsKey('attrs')){$entry.ExternalAttributes=$spec.attrs};$output=$entry.Open();try{[byte[]]$bytes=@();if($spec.ContainsKey('bytes')){$bytes=$spec.bytes}else{$bytes=[Text.Encoding]::UTF8.GetBytes($spec.text)};$output.Write($bytes,0,$bytes.Length)}finally{$output.Dispose()}}}finally{$zip.Dispose();$stream.Dispose()};return $path
}
function Write-Policy([string]$Name,$Value) {$path=Join-Path $fullWork ($Name+'.json');[IO.File]::WriteAllText($path,($Value|ConvertTo-Json -Depth 16),[Text.UTF8Encoding]::new($false));return $path}
function Invoke-Case([string]$Name,[string]$Archive,[string]$Policy,[int]$Exit,[string]$Code='',[string]$Output='') {
    $before=@{};foreach($path in @($Archive,$Policy)){if([IO.File]::Exists($path)){$before[$path]=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([IO.File]::ReadAllBytes($path)))}}
    $start=[Diagnostics.ProcessStartInfo]::new();$start.FileName=(Get-Process -Id $PID).Path;$start.UseShellExecute=$false;$start.RedirectStandardOutput=$true;$start.RedirectStandardError=$true
    foreach($arg in @('-NoLogo','-NoProfile','-File',$tool,'-ArchivePath',$Archive,'-PolicyPath',$Policy)){$start.ArgumentList.Add($arg)}
    if($Output -ne ''){$start.ArgumentList.Add('-ReportPath');$start.ArgumentList.Add($Output)}
    $process=[Diagnostics.Process]::Start($start);$stdout=$process.StandardOutput.ReadToEnd();$stderr=$process.StandardError.ReadToEnd();$process.WaitForExit()
    Assert ($process.ExitCode -eq $Exit) "$Name exit=$($process.ExitCode), expected=$Exit stdout=$stdout stderr=$stderr"
    Assert ($stderr -eq '') "$Name leaked stderr: $stderr"
    $report=$stdout|ConvertFrom-Json -Depth 16
    if($Code -ne ''){if($Exit -eq 2){Assert ($report.error -eq $Code) "$Name error=$($report.error), expected=$Code"}else{Assert (@($report.findings.code) -contains $Code) "$Name missing finding=$Code"}}
    Assert (-not $stdout.Contains($fullWork)) "$Name leaked an absolute input path"
    foreach($path in $before.Keys){Assert ($before[$path] -eq [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([IO.File]::ReadAllBytes($path)))) "$Name modified its input"}
    $script:count++;Write-Output "PASS $Name"
}
$good=Make-Zip 'good' @(@{name='README.txt';text="Orchard`n"},@{name='config/';text=''},@{name='config/demo.ini';text="[demo]`nmode=preview`n"})
$minimal=Write-Policy 'minimal' @{schemaVersion=1}
$valid=Write-Policy 'valid' @{schemaVersion=1;requiredMembers=@('README.txt','config/demo.ini');allowedMembers=@('README.txt','config/demo.ini');forbiddenMembers=@('private.env');textRules=@(@{member='config/demo.ini';containsAll=@('[demo]','mode=preview');containsNone=@('mode=production')})}
Invoke-Case 'minimal policy' $good $minimal 0
Invoke-Case 'literal policy' $good $valid 0
$hash=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([IO.File]::ReadAllBytes($good))).ToLowerInvariant()
Invoke-Case 'expected size hash' $good (Write-Policy 'hash' @{schemaVersion=1;expectedSha256=$hash;expectedSize=[IO.FileInfo]::new($good).Length}) 0
Invoke-Case 'hash mismatch' $good (Write-Policy 'bad-hash' @{schemaVersion=1;expectedSha256=('0'*64)}) 1 'archive_sha256_mismatch'
Invoke-Case 'hash final newline refused' $good (Write-Policy 'newline-hash' @{schemaVersion=1;expectedSha256=(('0'*64)+"`n")}) 2 'policy_invalid_sha256'
Invoke-Case 'size mismatch' $good (Write-Policy 'bad-size' @{schemaVersion=1;expectedSize=0}) 1 'archive_size_mismatch'
Invoke-Case 'missing required' $good (Write-Policy 'missing' @{schemaVersion=1;requiredMembers=@('missing.txt')}) 1 'required_member_missing'
Invoke-Case 'forbidden present' $good (Write-Policy 'forbidden' @{schemaVersion=1;forbiddenMembers=@('README.txt')}) 1 'forbidden_member_present'
Invoke-Case 'empty allowed denies files' $good (Write-Policy 'allowed' @{schemaVersion=1;allowedMembers=@()}) 1 'member_not_allowed'
Invoke-Case 'exact names case sensitive' $good (Write-Policy 'exact-case' @{schemaVersion=1;requiredMembers=@('readme.txt')}) 1 'required_member_missing'
Invoke-Case 'missing literal' $good (Write-Policy 'literal-missing' @{schemaVersion=1;textRules=@(@{member='README.txt';containsAll=@('Absent')})}) 1 'required_literal_missing'
Invoke-Case 'forbidden literal' $good (Write-Policy 'literal-forbidden' @{schemaVersion=1;textRules=@(@{member='README.txt';containsNone=@('Orchard')})}) 1 'forbidden_literal_present'
Invoke-Case 'missing text member' $good (Write-Policy 'text-missing' @{schemaVersion=1;textRules=@(@{member='missing.txt';containsAll=@('x')})}) 1 'text_member_missing'
Invoke-Case 'literal regex is not executed' $good (Write-Policy 'literal-regex' @{schemaVersion=1;textRules=@(@{member='README.txt';containsAll=@('.*')})}) 1 'required_literal_missing'
foreach($pair in @(@('unknown','{"schemaVersion":1,"x":1}','policy_unknown_field'),@('duplicate','{"schemaVersion":1,"schemaVersion":1}','policy_duplicate_field'),@('nested-duplicate','{"schemaVersion":1,"limits":{"maxEntries":1,"maxEntries":2}}','policy_duplicate_field'),@('wrong-type','{"schemaVersion":true}','policy_invalid_integer'),@('fraction','{"schemaVersion":1,"expectedSize":1.5}','policy_invalid_integer'),@('wrong-schema','{"schemaVersion":2}','policy_invalid_integer'),@('null-array','{"schemaVersion":1,"requiredMembers":null}','policy_invalid_array'),@('malformed','{"schemaVersion":','invalid_input'),@('duplicate-value','{"schemaVersion":1,"requiredMembers":["a","a"]}','policy_duplicate_value'),@('unsafe-policy','{"schemaVersion":1,"requiredMembers":["../a"]}','policy_unsafe_member'),@('contradiction','{"schemaVersion":1,"requiredMembers":["a"],"forbiddenMembers":["a"]}','policy_contradictory_members'),@('limit-over-hard-cap','{"schemaVersion":1,"limits":{"maxEntries":4097}}','policy_invalid_integer'),@('text-unknown','{"schemaVersion":1,"textRules":[{"member":"a","pattern":".*"}]}','policy_unknown_field'))){$p=Join-Path $fullWork ($pair[0]+'.json');[IO.File]::WriteAllText($p,$pair[1]);Invoke-Case $pair[0] $good $p 2 $pair[2]}
foreach($pair in @(@('traversal','../a'),@('absolute','/a'),@('drive','C:/a'),@('backslash','a\b'),@('empty-component','a//b'),@('dot-component','a/./b'),@('trailing-dot','a.'),@('device-name','NUL.txt'),@('control',"a`nb"))){Invoke-Case $pair[0] (Make-Zip $pair[0] @(@{name=$pair[1];text='x'})) $minimal 2 'zip_unsafe_member_name'}
Invoke-Case 'duplicate member' (Make-Zip 'duplicate-members' @(@{name='a';text='x'},@{name='a';text='y'})) $minimal 2 'zip_duplicate_or_portable_collision'
Invoke-Case 'case collision' (Make-Zip 'case-collision' @(@{name='a';text='x'},@{name='A';text='y'})) $minimal 2 'zip_duplicate_or_portable_collision'
Invoke-Case 'NFC collision' (Make-Zip 'nfc' @(@{name="caf$([char]0xe9)";text='x'},@{name="cafe$([char]0x301)";text='y'})) $minimal 2 'zip_duplicate_or_portable_collision'
Invoke-Case 'file parent collision' (Make-Zip 'parent-collision' @(@{name='a';text='x'},@{name='a/b';text='y'})) $minimal 2 'zip_file_directory_collision'
Invoke-Case 'symlink entry' (Make-Zip 'symlink' @(@{name='a';text='b';attrs=[int](-1577058304)})) $minimal 2 'zip_special_member_rejected'
Invoke-Case 'entry count cap' $good (Write-Policy 'count-cap' @{schemaVersion=1;limits=@{maxEntries=1}}) 2 'zip_metadata_limit'
Invoke-Case 'member size cap' $good (Write-Policy 'member-cap' @{schemaVersion=1;limits=@{maxMemberBytes=2}}) 2 'zip_member_size_limit'
Invoke-Case 'total size cap' $good (Write-Policy 'total-cap' @{schemaVersion=1;limits=@{maxTotalUncompressedBytes=10}}) 2 'zip_total_size_limit'
Invoke-Case 'text size cap' $good (Write-Policy 'text-cap' @{schemaVersion=1;limits=@{maxTextBytes=2};textRules=@(@{member='README.txt';containsAll=@('x')})}) 2 'zip_text_size_limit'
Invoke-Case 'invalid UTF8' (Make-Zip 'invalid-utf8' @(@{name='a';bytes=[byte[]]@(0xff,0xfe)})) (Write-Policy 'invalid-utf8-policy' @{schemaVersion=1;textRules=@(@{member='a';containsAll=@('x')})}) 2 'invalid_input'
$empty=Make-Zip 'empty' @();Invoke-Case 'empty archive' $empty $minimal 0
$bad=Join-Path $fullWork 'not-zip.zip';[IO.File]::WriteAllBytes($bad,[byte[]]@(1,2,3));Invoke-Case 'invalid archive' $bad $minimal 2 'zip_invalid_structure'
$edited=[IO.File]::ReadAllBytes($good);$edited[30]=[byte]([int]$edited[30]+1);$bad=Join-Path $fullWork 'local-name.zip';[IO.File]::WriteAllBytes($bad,$edited);Invoke-Case 'local central disagreement' $bad $minimal 2 'zip_local_name_mismatch'
$edited=[IO.File]::ReadAllBytes($good);$edited[8]=99;$bad=Join-Path $fullWork 'local-method.zip';[IO.File]::WriteAllBytes($bad,$edited);Invoke-Case 'local method disagreement' $bad $minimal 2 'zip_invalid_structure'
$edited=[IO.File]::ReadAllBytes($good);$edited[6]=$edited[6] -bxor 1;$bad=Join-Path $fullWork 'local-flags.zip';[IO.File]::WriteAllBytes($bad,$edited);Invoke-Case 'local flags disagreement' $bad $minimal 2 'zip_invalid_structure'
$edited=[IO.File]::ReadAllBytes($good);$edited[$edited.Length-12]=255;$edited[$edited.Length-11]=255;$bad=Join-Path $fullWork 'zip64.zip';[IO.File]::WriteAllBytes($bad,$edited);Invoke-Case 'ZIP64 count rejected' $bad $minimal 2 'zip_multidisk_or_zip64_unsupported'
$hugePolicy=Join-Path $fullWork 'huge-policy.json';[IO.File]::WriteAllText($hugePolicy,(' '*1048577));Invoke-Case 'policy hard cap' $good $hugePolicy 2 'input_size_limit'
$textEntries=@();$textRules=@();for($i=0;$i -lt 5;$i++){$name="text$i.txt";$textEntries+=@{name=$name;text=('x'*262144)};$textRules+=@{member=$name;containsAll=@('x')}}
Invoke-Case 'global text cap' (Make-Zip 'global-text' $textEntries) (Write-Policy 'global-text-policy' @{schemaVersion=1;textRules=$textRules}) 2 'zip_text_size_limit'
$edited=[IO.File]::ReadAllBytes($good);$bad=Join-Path $fullWork 'trailing-junk.zip';[IO.File]::WriteAllBytes($bad,($edited+[byte[]]@(0)));Invoke-Case 'trailing junk' $bad $minimal 2 'zip_invalid_structure'
$large=Join-Path $fullWork 'too-large.zip';$largeStream=[IO.File]::Create($large);$largeStream.SetLength(67108865);$largeStream.Dispose();Invoke-Case 'archive hard cap' $large $minimal 2 'input_size_limit'
$reportPath=Join-Path $fullWork 'report.json';Invoke-Case 'new report' $good $valid 0 '' $reportPath
$reportHash=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([IO.File]::ReadAllBytes($reportPath)));Invoke-Case 'existing report refused' $good $valid 2 'invalid_input' $reportPath;Assert ($reportHash -eq [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([IO.File]::ReadAllBytes($reportPath)))) 'existing report modified'
Invoke-Case 'relative path refused' 'relative.zip' $minimal 2 'local_absolute_path_required'
Invoke-Case 'missing file refused' (Join-Path $fullWork 'absent.zip') $minimal 2 'input_file_required'
Write-Output "PASS total=$script:count; all input hashes unchanged; generated fixtures retained only in WorkRoot."
