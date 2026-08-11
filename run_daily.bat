@echo off
REM Windows Task Scheduler entry point for system-design-app.
REM Registered via: schtasks /create /tn "SystemDesignApp Daily" ^
REM   /tr "<this file's full path>" /sc daily /st 13:00
REM
REM %~dp0 resolves to this file's own directory, so it works no matter
REM where the project folder lives - no path to edit here.
cd /d "%~dp0"
"C:\Users\Admin\AppData\Roaming\Python\Python312\Scripts\uv.exe" run system-design-app
