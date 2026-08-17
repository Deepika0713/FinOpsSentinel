import unittest
from unittest.mock import MagicMock, patch
from myModule.azure_scanner import AzureResourceScanner

class TestAzureResourceScanner(unittest.TestCase):
    @patch('myModule.azure_scanner.DefaultAzureCredential')
    @patch('myModule.azure_scanner.ComputeManagementClient')
    @patch('myModule.azure_scanner.NetworkManagementClient')
    @patch('myModule.azure_scanner.SqlManagementClient')
    @patch('myModule.azure_scanner.MetricsClient')
    def setUp(self, mock_monitor_client_class, mock_sql_client_class, mock_network_client_class, mock_compute_client_class, mock_credential_class):
        self.subscription_id = "test-sub-1234"
        self.scanner = AzureResourceScanner(self.subscription_id)
        
        self.mock_compute_client = self.scanner.compute_client
        self.mock_network_client = self.scanner.network_client
        self.mock_sql_client = self.scanner.sql_client
        self.mock_monitor_client = self.scanner.monitor_client

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

    def test_scan_idle_sql_databases(self):
        server = MagicMock()
        server.id = "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Sql/servers/srv1"
        server.name = "srv1"
        self.mock_sql_client.servers.list.return_value = [server]

        db1 = MagicMock()
        db1.id = "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Sql/servers/srv1/databases/db1"
        db1.name = "db1"
        db1.location = "eastus"

        db_master = MagicMock()
        db_master.id = "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Sql/servers/srv1/databases/master"
        db_master.name = "master"
        db_master.location = "eastus"

        self.mock_sql_client.databases.list_by_server.return_value = [db1, db_master]

        metric_cpu = MagicMock()
        metric_cpu.name = "cpu_percent"
        ts_cpu = MagicMock()
        val_cpu1 = MagicMock(average=0.5)
        val_cpu2 = MagicMock(average=0.2)
        ts_cpu.data = [val_cpu1, val_cpu2]
        metric_cpu.timeseries = [ts_cpu]

        metric_dtu = MagicMock()
        metric_dtu.name = "dtu_consumption_percent"
        ts_dtu = MagicMock()
        val_dtu1 = MagicMock(average=0.1)
        val_dtu2 = MagicMock(average=0.3)
        ts_dtu.data = [val_dtu1, val_dtu2]
        metric_dtu.timeseries = [ts_dtu]

        metrics_response = MagicMock()
        metrics_response.metrics = [metric_cpu, metric_dtu]
        self.mock_monitor_client.query_resource.return_value = metrics_response

        results = self.scanner.scan_idle_sql_databases()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "db1")
        self.assertEqual(results[0]["status"], "Idle / Low Usage")
        self.assertEqual(results[0]["type"], "SqlDatabase")
        self.assertEqual(results[0]["estimated_monthly_cost_usd"], 15.00)

    def test_scan_all(self):
        self.mock_compute_client.disks.list.return_value = []
        self.mock_network_client.public_ip_addresses.list_all.return_value = []
        self.mock_sql_client.servers.list.return_value = []

        results = self.scanner.scan_all()
        self.assertEqual(results, [])

if __name__ == "__main__":
    unittest.main()
