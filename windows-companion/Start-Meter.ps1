param(
  [Parameter(Mandatory=$true)][string]$StateDirectory,
  [string]$ClockAddress,
  [ValidateSet('ultra','sd-pro')][string]$Profile = 'ultra',
  [ValidateSet('Preview','Test','Watch','Restore')][string]$Mode = 'Preview'
)
$ErrorActionPreference = 'Stop'
$uvCommand = Get-Command uv -ErrorAction Stop
$meterArgs = @('run','--project',$PSScriptRoot,'python',(Join-Path $PSScriptRoot 'meter.py'),'--state-dir',$StateDirectory,'--output',(Join-Path $PSScriptRoot 'preview.jpg'))
if ($Mode -ne 'Preview') {
  if (-not $ClockAddress) { throw 'Supply the clock address for device actions.' }
  $meterArgs += @('--host',$ClockAddress,'--profile',$Profile,('--'+$Mode.ToLowerInvariant()))
}
& $uvCommand.Source @meterArgs
if ($LASTEXITCODE -ne 0) { throw 'Meter stopped with an error. Review the output above.' }
