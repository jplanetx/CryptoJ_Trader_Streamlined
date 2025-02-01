@echo off
SETLOCAL EnableDelayedExpansion

:: Parse command line arguments
SET TestType=all
SET TestPath=
SET Coverage=false
SET Verbose=false

:parse_args
IF "%~1"=="" GOTO end_parse
IF /I "%~1"=="--type" SET TestType=%~2& SHIFT
IF /I "%~1"=="--path" SET TestPath=%~2& SHIFT
IF /I "%~1"=="--coverage" SET Coverage=true
IF /I "%~1"=="--verbose" SET Verbose=true
SHIFT
GOTO parse_args
:end_parse

:: Execute PowerShell script with parameters
SET PS_COMMAND=powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_tests.ps1"

IF /I "%TestType%"=="unit" SET PS_COMMAND=%PS_COMMAND% -TestType unit
IF /I "%TestType%"=="integration" SET PS_COMMAND=%PS_COMMAND% -TestType integration
IF /I "%TestType%"=="specific" (
    IF NOT "%TestPath%"=="" (
        SET PS_COMMAND=%PS_COMMAND% -TestType specific -TestPath "%TestPath%"
    )
)
IF "%Coverage%"=="true" SET PS_COMMAND=%PS_COMMAND% -Coverage
IF "%Verbose%"=="true" SET PS_COMMAND=%PS_COMMAND% -Verbose

:: Run the command
%PS_COMMAND%

:: Check for errors
IF ERRORLEVEL 1 (
    echo Test execution failed
    exit /b 1
) ELSE (
    echo Test execution completed successfully
    exit /b 0
)
