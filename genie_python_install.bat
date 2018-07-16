setlocal

REM %~dp0 expands to directory where this file lives
set BASEDIR=%~dp0

if not "%KITS_DIR%" == "" (
	if not exist "%BASEDIR%COPY_COMPLETE.txt" (
		@echo Incomplete distribution - please try again later
		exit/B 1
	)
)

REM Copy the files across
if "%1" == "" (
    set PYDIR=C:\Instrument\Apps\Python
) else (
    set PYDIR=%1
)
if not exist "%PYDIR%" (
    mkdir %PYDIR%
)
xcopy /q /s /e /h /i /d /y "%BASEDIR%\Python" "%PYDIR%"
if %errorlevel% neq 0 (
    echo "ERROR: Copying python to %PYDIR%"
	exit /B %errorlevel%
)

REM copy the build number file across
REM xcopy /q /s /e /h /i /d  "%BASEDIR%BUILD_NUMBER.txt" "%PYDIR%\BUILD_NUMBER.txt"
REM if %errorlevel% neq 0 (
    REM echo "ERROR: Copying build number"
	REM exit /B %errorlevel%
REM )

REM create a default ipython_config
cd /D %PYDIR%
set "PATH=%PYDIR%;%PYDIR%\DLLs;%PATH%"
set "PYTHONHOME=%PYDIR%"
%PYDIR%\python.exe Scripts\ipython.exe profile create
if %errorlevel% neq 0 (
    echo "ERROR: Creating profile %errorlevel%"
	exit /B %errorlevel%
)

REM exclude LocalSystem account used for running jenkins service 
if not "%UserProfile%" == "%SystemRoot%\system32\config\systemprofile" ( 
    REM auto copy the ipython_config
    copy %BASEDIR%ipython_config.py %UserProfile%\.ipython\profile_default\.
    if %errorlevel% neq 0 (
        echo "ERROR: Copying ipython profile %errorlevel%"
	    exit /B %errorlevel%
    )
)

echo genie_python installed to %PYDIR%
