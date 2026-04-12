set shell := ["powershell", "-NoProfile", "-Command"]

clean:
    $confirmation = Read-Host 'Are you sure you want to clean this project directory? Type "delete my stuff" to continue'; \
    if ($confirmation -ne 'delete my stuff') { throw 'Clean cancelled.' }; \
    $root = (Resolve-Path '.').Path; \
    if (-not (Test-Path (Join-Path $root 'pyproject.toml'))) { throw 'Refusing to clean: run this only from a project root (pyproject.toml required).' }; \
    $items = Get-ChildItem -LiteralPath $root -Force; \
    foreach ($item in $items) { \
        Remove-Item -LiteralPath $item.FullName -Recurse -Force -ErrorAction SilentlyContinue; \
    }; \
    Write-Host ('Clean complete for ' + $root + '.')
