from django.db import models


class EconomiaIoT(models.Model):
    empresa = models.CharField(max_length=100)

    energia_sem_iot = models.FloatField()
    energia_com_iot = models.FloatField()

    manutencao_sem_iot = models.FloatField()
    manutencao_com_iot = models.FloatField()

    paradas_sem_iot = models.FloatField()
    paradas_com_iot = models.FloatField()

    data = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.empresa
