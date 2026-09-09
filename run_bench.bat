@echo off
setlocal
if defined PYTHON goto custom_python
where py >nul 2>nul
if not errorlevel 1 goto python_launcher
python "%~dp0run_bench.py" --config "%~dp0config.json" %*
exit /b %errorlevel%

:python_launcher
py -3 "%~dp0run_bench.py" --config "%~dp0config.json" %*
exit /b %errorlevel%

:custom_python
"%PYTHON%" "%~dp0run_bench.py" --config "%~dp0config.json" %*
exit /b %errorlevel%
