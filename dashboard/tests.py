from django.test import TestCase
from django.urls import reverse

from .models import SensorData


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