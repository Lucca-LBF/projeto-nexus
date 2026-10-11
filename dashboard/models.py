from django.db import models


class EconomiaIoT(models.Model):
    energia_sem_iot = models.FloatField()
    manutencao_sem_iot = models.FloatField()
    paradas_sem_iot = models.FloatField()
    
    energia_com_iot = models.FloatField()
    manutencao_com_iot = models.FloatField()
    paradas_com_iot = models.FloatField()

    def __str__(self):
        return "Dados de Economia IoT"

class SensorData(models.Model):
    maquina = models.CharField(max_length=100)
    temperatura = models.FloatField()
    energia = models.FloatField()
    producao = models.IntegerField()
    status = models.CharField(max_length=20)

    data_hora = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.maquina
    manutencao_sem_iot = models.FloatField()
    manutencao_com_iot = models.FloatField()

    paradas_sem_iot = models.FloatField()
    paradas_com_iot = models.FloatField()

    data = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.empresa
