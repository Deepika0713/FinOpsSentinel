import unittest
from unittest.mock import MagicMock, patch
from myModule.azure_scanner import AzureResourceScanner

class TestAzureResourceScanner(unittest.TestCase):
    @patch('myModule.azure_scanner.DefaultAzureCredential')
    @patch('myModule.azure_scanner.ComputeManagementClient')
    @patch('myModule.azure_scanner.NetworkManagementClient')
    def setUp(self, mock_network_client_class, mock_compute_client_class, mock_credential_class):
        self.subscription_id = "test-sub-1234"
        self.scanner = AzureResourceScanner(self.subscription_id)
        
        # Keep references to the mock clients
        self.mock_compute_client = self.scanner.compute_client
        self.mock_network_client = self.scanner.network_client

    def test_scan_unattached_disks(self):
        # Setup mock disk data
        mock_disk_attached = MagicMock()
        mock_disk_attached.id = "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Compute/disks/disk1"
        mock_disk_attached.name = "disk1"
        mock_disk_attached.managed_by = "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Compute/virtualMachines/vm1"
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
        self.assertEqual(results[0]["estimated_monthly_cost_usd"], 1.60)

    def test_scan_unassigned_public_ips(self):
        # Setup mock public ip data
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
        self.assertEqual(results[0]["ip_address"], "5.6.7.8")

    def test_scan_unattached_nics(self):
        mock_nic_attached = MagicMock()
        mock_nic_attached.id = "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Network/networkInterfaces/nic1"
        mock_nic_attached.name = "nic1"
        mock_nic_attached.virtual_machine = MagicMock()
        mock_nic_attached.location = "eastus"

        mock_nic_unattached = MagicMock()
        mock_nic_unattached.id = "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Network/networkInterfaces/nic2"
        mock_nic_unattached.name = "nic2"
        mock_nic_unattached.virtual_machine = None
        mock_nic_unattached.location = "eastus"

        self.mock_network_client.network_interfaces.list_all.return_value = [mock_nic_attached, mock_nic_unattached]

        results = self.scanner.scan_unattached_nics()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "nic2")
        self.assertEqual(results[0]["status"], "Unattached")
        self.assertEqual(results[0]["type"], "NetworkInterface")
        self.assertEqual(results[0]["estimated_monthly_cost_usd"], 0.0)

    def test_scan_unassociated_nsgs(self):
        mock_nsg_associated = MagicMock()
        mock_nsg_associated.id = "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Network/networkSecurityGroups/nsg1"
        mock_nsg_associated.name = "nsg1"
        mock_nsg_associated.subnets = [MagicMock()]
        mock_nsg_associated.network_interfaces = []
        mock_nsg_associated.location = "eastus"

        mock_nsg_unassociated = MagicMock()
        mock_nsg_unassociated.id = "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Network/networkSecurityGroups/nsg2"
        mock_nsg_unassociated.name = "nsg2"
        mock_nsg_unassociated.subnets = []
        mock_nsg_unassociated.network_interfaces = []
        mock_nsg_unassociated.location = "eastus"

        self.mock_network_client.network_security_groups.list_all.return_value = [mock_nsg_associated, mock_nsg_unassociated]

        results = self.scanner.scan_unassociated_nsgs()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "nsg2")
        self.assertEqual(results[0]["status"], "Unassociated")
        self.assertEqual(results[0]["type"], "NetworkSecurityGroup")
        self.assertEqual(results[0]["estimated_monthly_cost_usd"], 0.0)

    def test_scan_unlinked_route_tables(self):
        mock_rt_linked = MagicMock()
        mock_rt_linked.id = "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Network/routeTables/rt1"
        mock_rt_linked.name = "rt1"
        mock_rt_linked.subnets = [MagicMock()]
        mock_rt_linked.location = "eastus"

        mock_rt_unlinked = MagicMock()
        mock_rt_unlinked.id = "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Network/routeTables/rt2"
        mock_rt_unlinked.name = "rt2"
        mock_rt_unlinked.subnets = []
        mock_rt_unlinked.location = "eastus"

        self.mock_network_client.route_tables.list_all.return_value = [mock_rt_linked, mock_rt_unlinked]

        results = self.scanner.scan_unlinked_route_tables()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "rt2")
        self.assertEqual(results[0]["status"], "Unlinked")
        self.assertEqual(results[0]["type"], "RouteTable")
        self.assertEqual(results[0]["estimated_monthly_cost_usd"], 0.0)

    def test_scan_all(self):
        # Mock all individual list methods
        self.mock_compute_client.disks.list.return_value = []
        self.mock_network_client.public_ip_addresses.list_all.return_value = []
        mock_nic = MagicMock(id="/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Network/networkInterfaces/nic1", virtual_machine=None, location="eastus")
        mock_nic.name = "nic1"
        self.mock_network_client.network_interfaces.list_all.return_value = [mock_nic]
        self.mock_network_client.network_security_groups.list_all.return_value = []
        self.mock_network_client.route_tables.list_all.return_value = []

        results = self.scanner.scan_all()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["type"], "NetworkInterface")
        self.assertEqual(results[0]["name"], "nic1")

if __name__ == "__main__":
    unittest.main()
