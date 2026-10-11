@echo off
echo Atualizando o banco de dados...
python manage.py makemigrations
python manage.py migrate

echo Iniciando o servidor NEXUS...
python manage.py runserver