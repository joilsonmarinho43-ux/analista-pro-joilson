@echo off
echo ====================================
echo CORRIGINDO ERRO DE GIT
echo ====================================
echo.
echo 1. Removendo arquivos problemáticos...
del ACESSO_RAPIDO.bat
echo.
echo 2. Inicializando Git...
git init
echo.
echo 3. Adicionando arquivos...
git add .
echo.
echo 4. Fazendo commit...
git commit -m "Versão final corrigida"
echo.
echo 5. Adicionando remoto...
git remote add origin https://github.com/joilsonmarinho43-ux/analista-pro-joilson.git
echo.
echo 6. Enviando para GitHub...
git push -u origin main
echo.
echo ====================================
echo ✅ PROCESSO CONCLUÍDO!
echo.
pause
