@echo off
title FOURLEAFCLOVIS Archaeological Atlas
cd /d "%~dp0"
echo.
echo  FOURLEAFCLOVIS Archaeological Atlas
echo  =====================================
echo  Starting on http://localhost:8050
echo.
python -m atlas.gui.app
pause
