"Ensure hyperg is started"

$HyperdriveProcess = Get-Process hyperg -ErrorAction SilentlyContinue

if ($HyperdriveProcess) {
  Stop-Process -Id $HyperdriveProcess.Id
}
"Test..."
$env:path

"Starting..."
where.exe hyperg

$HyperdriveProcess = Start-Process C:\BuildResources\hyperg\hyperg.exe -WorkingDirectory C:\Users\buildbot-worker -PassThru

Start-Sleep -s 5

$HyperdriveProcess

$HyperdriveProcess.Id | Out-File .test-daemon-hyperg.pid
