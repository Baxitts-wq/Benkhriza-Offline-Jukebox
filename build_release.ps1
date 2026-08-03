$ErrorActionPreference = "Stop"

python -m pip install -r requirements-dev.txt
python -m PyInstaller --clean --noconfirm MrBenkrizaDownloader_release.spec

Write-Host ""
Write-Host "Release build created in dist\MrBenkrizaDownloader.exe"
Write-Host "Private cookies, downloads, build cache, and .env files are excluded by .gitignore."
