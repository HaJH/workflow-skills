@echo off
rem Open the work board from cmd: "scripts\board" opens the kanban page, "scripts\board ready"
rem prints the verdict. A bare "bash" in cmd can resolve to the WSL launcher, so this runs
rem scripts/board with the bash.exe of the Git for Windows install that provides git.
setlocal
set "GITBASH="
for /f "delims=" %%G in ('where git 2^>nul') do if not defined GITBASH if exist "%%~dpG..\bin\bash.exe" set "GITBASH=%%~dpG..\bin\bash.exe"
if not defined GITBASH (
    echo board: Git Bash not found - install Git for Windows, or run "bash scripts/board" from Git Bash 1>&2
    exit /b 2
)
set "HERE=%~dp0"
"%GITBASH%" "%HERE:\=/%board" %*
