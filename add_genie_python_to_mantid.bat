REM this allows genie python to be imported into Mantid
REM it copies genie python into the mantid python site packages area and
REM install additional requirements
setlocal
set "MANTIDROOT=C:\MantidInstall"
robocopy "%~dp0Lib\site-packages\genie_python" "%MANTIDROOT%\bin\Lib\site-packages\genie_python" /mir /nfl /ndl /np /log:nul
xcopy /q /y "%~dp0caRepeater.exe" "%MANTIDROOT%\bin"
%MANTIDROOT%\bin\Scripts\pip.exe install -r %~dp0mantid_requirements.txt
