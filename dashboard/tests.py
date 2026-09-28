from django.test import TestCase
from django.urls import reverse

from .models import SensorData


class SensorDataModelTest(TestCase):

    def test_criar_sensor_data(self):
        dado = SensorData.objects.create(
            maquina="Máquina 01",
            temperatura=75.5,
            energia=100.0,
            producao=500,
            status="Normal",
        )
