@echo off

echo Loading environment variables...

for /f "tokens=1,* delims==" %%a in (.env) do (
    set %%a=%%b
    echo %%a=%%b
)

echo Environment variables loaded successfully!