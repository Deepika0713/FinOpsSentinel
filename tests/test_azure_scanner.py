import unittest
from unittest.mock import MagicMock, patch
from myModule.azure_scanner import AzureResourceScanner
from datetime import datetime, timezone, timedelta

class TestAzureResourceScanner(unittest.TestCase):
    @patch('myModule.azure_scanner.DefaultAzureCredential')
    @patch('myModule.azure_scanner.ComputeManagementClient')
    @patch('myModule.azure_scanner.NetworkManagementClient')
    @patch('myModule.azure_scanner.WebSiteManagementClient')
    def setUp(self, mock_web_client_class, mock_network_client_class, mock_compute_client_class, mock_credential_class):
        self.subscription_id = "test-sub-1234"
        self.scanner = AzureResourceScanner(self.subscription_id)
        
        self.mock_compute_client = self.scanner.compute_client
        self.mock_network_client = self.scanner.network_client
        self.mock_web_client = self.scanner.web_client

    def test_scan_unattached_disks(self):
        mock_disk_attached = MagicMock()
        mock_disk_attached.id = "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Compute/disks/disk1"
        mock_disk_attached.name = "disk1"
        mock_disk_attached.managed_by = "some-vm"
        mock_disk_attached.disk_size_gb = 128
        mock_disk_attached.location = "eastus"

        mock_disk_unattached = MagicMock()
        mock_disk_unattached.id = "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Compute/disks/disk2"
        mock_disk_unattached.name = "disk2"
        mock_disk_unattached.managed_by = None
        mock_disk_unattached.disk_size_gb = 32
        mock_disk_unattached.location = "eastus"

        self.mock_compute_client.disks.list.return_value = [mock_disk_attached, mock_disk_unattached]

        results = self.scanner.scan_unattached_disks()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "disk2")
        self.assertEqual(results[0]["status"], "Unattached")

    def test_scan_unassigned_public_ips(self):
        mock_ip_assigned = MagicMock()
        mock_ip_assigned.id = "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Network/publicIPAddresses/ip1"
        mock_ip_assigned.name = "ip1"
        mock_ip_assigned.ip_configuration = MagicMock()
        mock_ip_assigned.ip_address = "1.2.3.4"
        mock_ip_assigned.location = "eastus"

        mock_ip_unassigned = MagicMock()
        mock_ip_unassigned.id = "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Network/publicIPAddresses/ip2"
        mock_ip_unassigned.name = "ip2"
        mock_ip_unassigned.ip_configuration = None
        mock_ip_unassigned.ip_address = "5.6.7.8"
        mock_ip_unassigned.location = "eastus"

        self.mock_network_client.public_ip_addresses.list_all.return_value = [mock_ip_assigned, mock_ip_unassigned]

        results = self.scanner.scan_unassigned_public_ips()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "ip2")
        self.assertEqual(results[0]["status"], "Unassociated")

    def test_scan_empty_app_service_plans(self):
        plan1 = MagicMock()
        plan1.id = "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Web/serverfarms/plan1"
        plan1.name = "plan1"
        plan1.location = "eastus"
        plan1.number_of_sites = 0
        plan1.sku.tier = "Standard"

        plan2 = MagicMock()
        plan2.id = "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Web/serverfarms/plan2"
        plan2.name = "plan2"
        plan2.location = "eastus"
        plan2.number_of_sites = 0
        plan2.sku.tier = "Free"

        plan3 = MagicMock()
        plan3.id = "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Web/serverfarms/plan3"
        plan3.name = "plan3"
        plan3.location = "eastus"
        plan3.number_of_sites = 1
        plan3.sku.tier = "PremiumV2"

        self.mock_web_client.app_service_plans.list.return_value = [plan1, plan2, plan3]

        results = self.scanner.scan_empty_app_service_plans()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "plan1")
        self.assertEqual(results[0]["status"], "Empty")
        self.assertEqual(results[0]["type"], "AppServicePlan")

    def test_scan_aged_snapshots(self):
        now = datetime.now(timezone.utc)

        snap1 = MagicMock()
        snap1.id = "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Compute/snapshots/snap1"
        snap1.name = "snap1"
        snap1.location = "eastus"
        snap1.disk_size_gb = 50
        snap1.time_created = now - timedelta(days=100)

        snap2 = MagicMock()
        snap2.id = "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Compute/snapshots/snap2"
        snap2.name = "snap2"
        snap2.location = "eastus"
        snap2.disk_size_gb = 100
        snap2.time_created = now - timedelta(days=10)

        self.mock_compute_client.snapshots.list.return_value = [snap1, snap2]

        results = self.scanner.scan_aged_snapshots()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "snap1")
        self.assertEqual(results[0]["status"], "Aged")
        self.assertEqual(results[0]["type"], "Snapshot")
        self.assertEqual(results[0]["estimated_monthly_cost_usd"], 2.50)

    def test_scan_all(self):
        self.mock_compute_client.disks.list.return_value = []
        self.mock_network_client.public_ip_addresses.list_all.return_value = []
        self.mock_web_client.app_service_plans.list.return_value = []
        self.mock_compute_client.snapshots.list.return_value = []

        results = self.scanner.scan_all()
        self.assertEqual(results, [])

if __name__ == "__main__":
    unittest.main()
