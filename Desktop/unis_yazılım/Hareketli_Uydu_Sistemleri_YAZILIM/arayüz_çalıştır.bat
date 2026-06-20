@echo off
setlocal
cd /d "%~dp0"
echo =============================================
echo  Mergen Terminal Kontrol Sistemi v2.0
echo  Once bagimliliklari yukleyin:
echo    pip install -r arayuz\requirements.txt
echo =============================================
python -m arayuz.main
pause
