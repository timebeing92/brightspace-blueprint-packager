@echo off
rem Double-clickable launcher for the Blueprint Packager (Windows).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0blueprint_packager.ps1" %*
if errorlevel 1 pause
