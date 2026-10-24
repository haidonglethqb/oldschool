<#
.SYNOPSIS
    Script cai dat va khoi chay tu dong tu A-Z cho He thong Quan ly Kho Old School.
.DESCRIPTION
    Tu dong thuc hien toan bo quy trinh cho nguoi moi clone repo ve:
    1. Tim Python 3 tren may (neu may chua cai Python, tu dong cai Python 3.12 qua winget) & tao .venv
    2. Cai dat day du thu vien trong requirements.txt
    3. Tu dong tao file .env tu .env.example (dung SQLite chay ngay, khong can cai PostgreSQL)
    4. Chay migrate khoi tao cau truc Co so du lieu
    5. Khoi tao du lieu mau (Mac dinh: 2 co so CS1 & CS2; ho tro -Branches 3 cho 3 co so)
    6. Tu dong mo trinh duyet va khoi chay Web Server tai http://127.0.0.1:8000/

.PARAMETER Branches
    So luong co so du lieu mau muon tao: 2 (mac dinh: CS1 & CS2) hoac 3 (CS1, CS2, CS3).
.PARAMETER ResetDb
    Xoa co so du lieu SQLite hien tai (db.sqlite3) de lam moi hoan toan tu dau.
.PARAMETER NoServer
    Chi cai dat va tao du lieu mau, khong tu dong bat runserver o buoc cuoi.
#>

param(
    [ValidateSet(2, 3)]
    [int]$Branches = 2,
    [switch]$ResetDb,
    [switch]$NoServer
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "   OLD SCHOOL - THIET LAP HE THONG TU DONG TU A DEN Z" -ForegroundColor Yellow
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

# ----------------------------------------------------------------------
# BUOC 1: Tim Python 3 hop le (hoac tu cai qua winget) va tao .venv
# ----------------------------------------------------------------------
Write-Host "[1/6] Kiem tra moi truong Python & Virtual Environment (.venv)..." -ForegroundColor Green

$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

function Test-PythonExe {
    param([string]$ExePath, [string[]]$ExtraArgs = @())
    try {
        $out = & $ExePath @ExtraArgs -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        if ($LASTEXITCODE -eq 0 -and $out -match '^\d+\.\d+$') {
            return $true
        }
    } catch {}
    return $false
}

function Find-SystemPython {
    if (Get-Command "py" -ErrorAction SilentlyContinue) {
        if (Test-PythonExe "py" @("-3")) {
            return @{ Exe = "py"; Args = @("-3") }
        }
    }
    if (Get-Command "python" -ErrorAction SilentlyContinue) {
        if (Test-PythonExe "python") {
            return @{ Exe = "python"; Args = @() }
        }
    }
    if (Get-Command "python3" -ErrorAction SilentlyContinue) {
        if (Test-PythonExe "python3") {
            return @{ Exe = "python3"; Args = @() }
        }
    }

    $CandidatePatterns = @(
        "$env:LOCALAPPDATA\Programs\Python\Python3*\python.exe",
        "C:\Python3*\python.exe",
        "$env:ProgramFiles\Python3*\python.exe",
        "$env:USERPROFILE\miniconda3\python.exe",
        "$env:USERPROFILE\anaconda3\python.exe",
        "$env:USERPROFILE\.cache\codex-runtimes\*\dependencies\python\python.exe"
    )
    foreach ($pattern in $CandidatePatterns) {
        $found = Get-Item $pattern -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | Select-Object -First 1
        if ($found -and (Test-PythonExe $found.FullName)) {
            return @{ Exe = $found.FullName; Args = @() }
        }
    }
    return $null
}

if (-not (Test-Path $VenvPython)) {
    Write-Host "  -> Chua co .venv. Dang tim kiem Python 3 tren may..." -ForegroundColor Gray
    $PyInfo = Find-SystemPython

    # Neu may chua cai Python, tu dong cai Python 3.12 bang winget
    if (-not $PyInfo -and (Get-Command "winget" -ErrorAction SilentlyContinue)) {
        Write-Host "  -> May chua co Python. Dang tu dong cai dat Python 3.12 qua winget..." -ForegroundColor Yellow
        winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
        $env:PATH = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
        $PyInfo = Find-SystemPython
    }

    if (-not $PyInfo) {
        Write-Host "[LOI] Khong tim thay Python 3.10+ tren may tinh cua ban!" -ForegroundColor Red
        Write-Host "Vui long tai va cai dat Python 3.12 tai: https://www.python.org/downloads/" -ForegroundColor Yellow
        exit 1
    }

    $BasePython = $PyInfo.Exe
    $BasePythonArgs = $PyInfo.Args

    Write-Host "  -> Dang tao moi truong ao .venv bang: $BasePython $($BasePythonArgs -join ' ')" -ForegroundColor Gray
    & $BasePython @BasePythonArgs -m venv ".venv"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[LOI] Khong the tao moi truong ao .venv." -ForegroundColor Red
        exit 1
    }
    Write-Host "  -> Da tao .venv thanh cong!" -ForegroundColor Green
} else {
    Write-Host "  -> Da tim thay moi truong ao .venv." -ForegroundColor Gray
}

# ----------------------------------------------------------------------
# BUOC 2: Cai dat cac thu vien trong requirements.txt
# ----------------------------------------------------------------------
Write-Host ""
Write-Host "[2/6] Cai dat cac goi thu vien tu requirements.txt..." -ForegroundColor Green
& $VenvPython -m pip install --disable-pip-version-check -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "[LOI] Qua trinh cai dat thu vien that bai." -ForegroundColor Red
    exit 1
}

# ----------------------------------------------------------------------
# BUOC 3: Khoi tao file cau hinh .env (neu chua ton tai)
# ----------------------------------------------------------------------
Write-Host ""
Write-Host "[3/6] Kiem tra file cau hinh moi truong (.env)..." -ForegroundColor Green
$EnvFile = Join-Path $ProjectRoot ".env"
$EnvExampleFile = Join-Path $ProjectRoot ".env.example"

if (-not (Test-Path $EnvFile)) {
    if (Test-Path $EnvExampleFile) {
        Copy-Item $EnvExampleFile $EnvFile
        Write-Host "  -> Da tu dong tao file .env tu .env.example (Mac dinh dung SQLite chay ngay)." -ForegroundColor Gray
    } else {
        @"
DEBUG=True
SECRET_KEY=django-insecure-oldschool-dev-secret-key-change-in-production
ALLOWED_HOSTS=127.0.0.1,localhost,testserver
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3
CENTRAL_WAREHOUSE_CODE=CS1
MAX_UPLOAD_SIZE_MB=10
"@ | Set-Content -Path $EnvFile -Encoding UTF8
        Write-Host "  -> Da tao file .env mac dinh." -ForegroundColor Gray
    }
} else {
    Write-Host "  -> File .env da ton tai, giu nguyen cau hinh hien hanh." -ForegroundColor Gray
}

# ----------------------------------------------------------------------
# BUOC 4: Xu ly lam sach DB (neu yeu cau -ResetDb hoac chuyen tu 3 ve 2 co so)
# ----------------------------------------------------------------------
Write-Host ""
Write-Host "[4/6] Kiem tra trang thai Co so du lieu..." -ForegroundColor Green
$SqliteFile = Join-Path $ProjectRoot "db.sqlite3"

if ($ResetDb -and (Test-Path $SqliteFile)) {
    Remove-Item $SqliteFile -Force
    Write-Host "  -> Da xoa db.sqlite3 cu theo tuy chon -ResetDb." -ForegroundColor Yellow
} elseif (($Branches -eq 2) -and (Test-Path $SqliteFile)) {
    $hasCs3 = & $VenvPython -c "import os, django; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings'); django.setup(); from apps.branches.models import CoSo; print('YES' if CoSo.objects.filter(ma_co_so='CS3').exists() else 'NO')" 2>$null
    if ($hasCs3 -match "YES") {
        Remove-Item $SqliteFile -Force
        Write-Host "  -> Phat hien DB cu co CS3, tu dong lam moi DB de chuan hoa ve dung 2 co so (CS1 & CS2)." -ForegroundColor Yellow
    }
}

# ----------------------------------------------------------------------
# BUOC 5: Chay Migration & Khoi tao du lieu mau (Seed Data)
# ----------------------------------------------------------------------
Write-Host ""
Write-Host "[5/6] Chay Django Migrations va khoi tao du lieu mau ($Branches co so)..." -ForegroundColor Green
& $VenvPython manage.py migrate
if ($LASTEXITCODE -ne 0) {
    Write-Host "[LOI] Khong the chay lenh migrate." -ForegroundColor Red
    exit 1
}

if ($Branches -eq 3) {
    & $VenvPython manage.py seed_oldschool_3b
} else {
    & $VenvPython manage.py seed_oldschool
}
if ($LASTEXITCODE -ne 0) {
    Write-Host "[LOI] Khong the khoi tao du lieu mau." -ForegroundColor Red
    exit 1
}

# ----------------------------------------------------------------------
# BUOC 6: Hoan tat, Tu dong mo Trinh duyet & Khoi chay Server
# ----------------------------------------------------------------------
Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "   HOAN TAT CAI DAT! HE THONG DA SAN SANG SU DUNG" -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  URL truy cap    : http://127.0.0.1:8000/" -ForegroundColor Yellow
Write-Host "  Mat khau chung  : OldSchool@123" -ForegroundColor Yellow
Write-Host "  Tai khoan Demo  :" -ForegroundColor White
Write-Host "    - Chu cua hang (Admin) : admin_owner" -ForegroundColor Gray
Write-Host "    - Quan ly CS1 (Kho)    : manager_cs1" -ForegroundColor Gray
Write-Host "    - Quan ly CS2          : manager_cs2" -ForegroundColor Gray
Write-Host "    - Nhan vien CS1        : staff_cs1" -ForegroundColor Gray
Write-Host "    - Nhan vien CS2        : staff_cs2" -ForegroundColor Gray
if ($Branches -eq 3) {
    Write-Host "    - Quan ly CS3          : manager_cs3" -ForegroundColor Gray
    Write-Host "    - Nhan vien CS3        : staff_cs3" -ForegroundColor Gray
}
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

if (-not $NoServer) {
    Write-Host "[6/6] Dang mo trinh duyet va khoi dong Web Server tai http://127.0.0.1:8000/ (Nhan Ctrl+C de dung)..." -ForegroundColor Green
    Start-Process "http://127.0.0.1:8000/"
    & $VenvPython manage.py runserver 8000
} else {
    Write-Host "[6/6] Da bo qua buoc bat server (-NoServer). De chay server, go: .\start.bat" -ForegroundColor Green
}
