# Usage (from repo root):  . .\scripts\dev.ps1 [-Client ZestWear]
param([string]$Client = "FinBank")

$global:base = "http://127.0.0.1:8000"
$sql = "select a.id, c.id from agencies a join clients c on c.agency_id=a.id where a.name='Brandly Seed Agency' and c.name='$Client' limit 1"
$row = docker exec brandly-db psql -U brandly -d brandly -t -A -F "," -c $sql
if ($row) {
  $global:aid, $global:cid = $row.Trim().Split(",")
  $global:h = @{ "X-Agency-Id" = $global:aid }
  "client=$Client  agency=$global:aid  cid=$global:cid"
} else {
  "No '$Client' client in the seed agency. Run from backend: python -m app.seed"
}

function global:Gen([string]$Task) {
  $body = @{ task = $Task } | ConvertTo-Json
  $r = Invoke-WebRequest -UseBasicParsing -Method Post -Uri "$global:base/clients/$global:cid/generate" -Headers $global:h -ContentType "application/json" -Body $body
  [Text.Encoding]::UTF8.GetString($r.RawContentStream.ToArray()) | ConvertFrom-Json
}
