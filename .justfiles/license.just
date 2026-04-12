set shell := ["powershell", "-NoProfile", "-Command"]

# Select and download a software license from scancode-licensedb.
license:
    $indexUrl = 'https://scancode-licensedb.aboutcode.org/index.json'; \
    $all = Invoke-RestMethod -Uri $indexUrl -TimeoutSec 30; \
    $licenses = $all | Where-Object { -not $_.is_exception -and -not $_.is_deprecated -and $_.license } | Sort-Object spdx_license_key, license_key; \
    if (-not $licenses -or $licenses.Count -eq 0) { throw 'No licenses found in remote index.' }; \
    Write-Host ('Found ' + $licenses.Count + ' licenses.'); \
    $query = Read-Host 'Filter licenses by text (blank for all)'; \
    if ($query) { $licenses = $licenses | Where-Object { (($_.spdx_license_key) -and ($_.spdx_license_key -match [regex]::Escape($query))) -or (($_.license_key) -and ($_.license_key -match [regex]::Escape($query))) } }; \
    for ($i = 0; $i -lt $licenses.Count; $i++) { Write-Host ([string]($i + 1) + '. ' + $(if ($licenses[$i].spdx_license_key) { $licenses[$i].spdx_license_key } else { $licenses[$i].license_key })) }; \
    $selection = Read-Host 'Enter number'; \
    [int]$parsed = 0; \
    if (-not [int]::TryParse($selection, [ref]$parsed)) { throw 'Invalid selection.' }; \
    $chosen = $licenses[$parsed - 1]; \
    Invoke-WebRequest -UseBasicParsing -Uri ('https://scancode-licensedb.aboutcode.org/' + $chosen.license) -OutFile 'LICENSE'; \
    Write-Host ('Downloaded ' + $(if ($chosen.spdx_license_key) { $chosen.spdx_license_key } else { $chosen.license_key }) + ' to LICENSE')
