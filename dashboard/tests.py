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
        self.assertEqual(dado.maquina, "Máquina 01")
        self.assertEqual(dado.temperatura, 75.5)
        self.assertEqual(dado.energia, 100.0)
        self.assertEqual(dado.producao, 500)
        self.assertEqual(dado.status, "Normal")
class DashboardTest(TestCase):

    def test_dashboard_carrega(self):
        SensorData.objects.create(
            maquina="Máquina 01",
            temperatura=75.0,
            energia=100.0,
            producao=500,
            status="Normal",
        )
        response = self.client.get(
            reverse("dashboard")
        )

        self.assertEqual(response.status_code, 200)