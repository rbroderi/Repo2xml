prek-init:
    if (-not (Test-Path 'pyproject.toml')) { throw 'pyproject.toml not found.' }; \
    $projectNameMatch = Select-String -Path 'pyproject.toml' -Pattern '^\s*name\s*=\s*"([^\"]+)"' -AllMatches | Select-Object -First 1; if (-not $projectNameMatch -or $projectNameMatch.Matches.Count -eq 0) { throw 'project.name not found in pyproject.toml.' }; $projectName = $projectNameMatch.Matches[0].Groups[1].Value; \
    $packageName = $projectName -replace '-', '_'; \
    uv add --optional dev prek; \
    uv run prek install

prek:
    uv run prek run --all-files; uv run prek run --all-files
