@echo off
rem L'interprete del progetto per cmd e PowerShell, stessa regola di bin/py:
rem prima DIVARIO_PYTHON, poi .venv del repo, poi VIRTUAL_ENV. Mai un interprete di un altro worktree.
setlocal
set "HERE=%~dp0.."
if defined DIVARIO_PYTHON if exist "%DIVARIO_PYTHON%" "%DIVARIO_PYTHON%" %* & exit /b %errorlevel%
if exist "%HERE%\.venv\Scripts\python.exe" "%HERE%\.venv\Scripts\python.exe" %* & exit /b %errorlevel%
if defined VIRTUAL_ENV if exist "%VIRTUAL_ENV%\Scripts\python.exe" "%VIRTUAL_ENV%\Scripts\python.exe" %* & exit /b %errorlevel%
echo bin\py: nessun interprete con le dipendenze del progetto. 1>&2
echo Cercati, in ordine: DIVARIO_PYTHON, %HERE%\.venv\Scripts\python.exe, VIRTUAL_ENV\Scripts\python.exe 1>&2
echo Crealo qui:  uv venv .venv ^&^& uv pip install -r requirements.txt 1>&2
exit /b 127
