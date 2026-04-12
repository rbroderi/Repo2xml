# Create GitHub automation files (.github/dependabot.yml and workflows).
github-actions-init:
    $pyprojectPath = 'pyproject.toml'; \
    if (-not (Test-Path $pyprojectPath)) { throw 'pyproject.toml not found. Run this from your project root.' }; \
    $pythonVersion = '3.13'; \
    $requiresMatch = Select-String -Path $pyprojectPath -Pattern '^requires-python\s*=\s*">=([0-9]+\.[0-9]+)"' -AllMatches | Select-Object -First 1; \
    if ($requiresMatch -and $requiresMatch.Matches.Count -gt 0) { $pythonVersion = $requiresMatch.Matches[0].Groups[1].Value }; \
    Write-Host ('Python version: ' + $pythonVersion)
