@echo off
rem Lance VirtuLouvre sous Windows (double-clic).
rem Au premier lancement, cree un environnement Python (.venv) et installe les dependances.
rem pushd (et pas cd) : marche aussi depuis un dossier reseau \\serveur\partage
pushd "%~dp0" || (echo Impossible d'ouvrir le dossier du jeu : %~dp0 & pause & exit /b 1)

.venv\Scripts\python -c "import pygame, OpenGL, numpy" >nul 2>&1
if errorlevel 1 (
    echo Premier lancement : installation des dependances...
    rem --clear : repart de zero si un ancien .venv est casse, par exemple apres une mise a jour de Python
    py -3 -m venv --clear .venv >nul 2>&1 || python -m venv --clear .venv || goto erreur
    .venv\Scripts\python -m pip install -r requirements.txt || goto erreur
)

.venv\Scripts\python main.py %*
if errorlevel 1 pause
popd
exit /b

:erreur
echo.
echo Installation impossible. Installe Python 3.9 ou plus recent depuis https://www.python.org/downloads/
echo (coche "Add python.exe to PATH" pendant l'installation), puis relance ce fichier.
pause
popd
exit /b 1
