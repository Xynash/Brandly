# Usage (from repo root):  . .\scripts\dev.ps1
$global:base = "http://127.0.0.1:8000"
$row = docker exec brandly-db psql -U brandly -d brandly -t -A -F "," -c "select a.id, c.id from agencies a join clients c on c.agency_id=a.id where c.name='FinBank' order by c.created_at desc limit 1"
if ($row) {
  $global:aid, $global:cid = $row.Trim().Split(",")
  $global:h = @{ "X-Agency-Id" = $global:aid }
  "base=$global:base  agency=$global:aid  client=$global:cid"
} else {
  "No FinBank client found. Create one first."
}
