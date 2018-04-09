@echo off

setlocal

set MYDIR=%~dp0

if "%GENIE_SIMULATE%" == "" (
    set GENIE_SIMULATE=0
)

REM Add CaRepeater to path
set "PATH=%MYDIR%EPICS_UTILS;%PATH%"

REM Set up address list
call %MYDIR%get_isis_ip.bat

set EPICS_CA_ADDR_LIST=127.255.255.255 %ISISBCAST% 130.246.39.152:5066 %EPICS_CA_ADDR_LIST%
set EPICS_CA_AUTO_ADDR_LIST=NO

REM spectra are sent by CA so need to set to around 4 * (max num time channels)
REM default is set in base/configure/CONFIG_SITE_ENV - should set there too in case this variable gets unset 
set EPICS_CA_MAX_ARRAY_BYTES=65536
set PYTHONHOME=%MYDIR%
set PYTHONPATH=%MYDIR%

if "%1" == "" (
    %MYDIR%python.exe %MYDIR%Scripts\ipython.exe
) else (
    %MYDIR%python.exe %*
)
