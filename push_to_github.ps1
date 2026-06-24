&param(
    [string]$CommitMessage = "auto-update: $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
)

# Astra AI — автоматический push на GitHub
# Использует токен из data/github_config.json

$REPO = "psodhdh776/AstraAI"
$GIT_URL = "https://github.com/$REPO.git"
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$CONFIG_PATH = Join-Path $SCRIPT_DIR "data\github_config.json"

# Проверка Git
$gitCmd = (Get-Command "git" -ErrorAction SilentlyContinue)
if (-not $gitCmd) {
    Write-Host "[ERROR] Git не установлен." -ForegroundColor Red
    Write-Host "Скачайте: https://git-scm.com/download/win"
    exit 1
}

# Чтение токена
$token = ""
if (Test-Path $CONFIG_PATH) {
    try {
        $cfg = Get-Content $CONFIG_PATH -Raw | ConvertFrom-Json
        $token = $cfg.github_token
    } catch {
        Write-Host "[WARN] Не удалось прочитать $CONFIG_PATH" -ForegroundColor Yellow
    }
}

if (-not $token) {
    Write-Host "[ERROR] Токен не найден в $CONFIG_PATH" -ForegroundColor Red
    Write-Host "Создайте PAT на https://github.com/settings/tokens и сохраните в data/github_config.json:"
    Write-Host '  {"github_token": "github_pat_..."}'
    exit 1
}

Set-Location $SCRIPT_DIR

# Инициализация репозитория
if (-not (Test-Path ".git")) {
    Write-Host "[INIT] Инициализация репозитория..." -ForegroundColor Cyan
    git init
    git branch -M main
}

# Настройка remote
$remoteUrl = "https://psodhdh776:$token@github.com/$REPO.git"
$existing = git remote get-url origin 2>$null
if (-not $existing) {
    git remote add origin $remoteUrl
    Write-Host "[OK] Remote origin добавлен" -ForegroundColor Green
} elseif ($existing -ne $remoteUrl -and $existing -notlike "*$REPO*") {
    git remote set-url origin $remoteUrl
    Write-Host "[OK] Remote origin обновлён" -ForegroundColor Green
}

# Настройка user (для CI)
git config user.name "psodhdh776" 2>$null
git config user.email "psodhdh776@users.noreply.github.com" 2>$null

# Добавление файлов
Write-Host "[ADD] Добавление файлов..." -ForegroundColor Cyan
git add -A

# Статус
$status = git status --porcelain
if (-not $status) {
    Write-Host "[OK] Нет изменений для коммита" -ForegroundColor Green
    exit 0
}

# Коммит
Write-Host "[COMMIT] $CommitMessage" -ForegroundColor Cyan
git commit -m "$CommitMessage"

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Коммит не удался" -ForegroundColor Red
    exit 1
}

# Push
Write-Host "[PUSH] Отправка в $REPO (main)..." -ForegroundColor Cyan
git push -u origin main 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "[DONE] Успешно отправлено!" -ForegroundColor Green
    Write-Host "      https://github.com/$REPO"
} else {
    Write-Host "[ERROR] Push не удался. Проверьте токен и доступ к репозиторию." -ForegroundColor Red
    exit 1
}
