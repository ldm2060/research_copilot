@echo off
REM Research Copilot Guard wrapper (Windows).
REM Tries to run the Python guard; if Python is unavailable, emits an
REM allow decision so the prompt-based fallback hook can take over.
REM Reads hook payload from stdin and pipes it to Python.

where python >nul 2>&1
if %errorlevel% equ 0 (
    python "%~dp0research_copilot_guard.py"
    exit /b %errorlevel%
)

where python3 >nul 2>&1
if %errorlevel% equ 0 (
    python3 "%~dp0research_copilot_guard.py"
    exit /b %errorlevel%
)

echo {"hookSpecificOutput":{"permissionDecision":"allow"},"systemMessage":"research-copilot-guard: Python unavailable; deferring to prompt-based fallback and skill HARD-GATE blocks."}
exit /b 0
