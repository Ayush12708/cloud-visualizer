import os
import datetime
from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.monitor import MonitorManagementClient
from azure.mgmt.costmanagement import CostManagementClient
from azure.core.exceptions import ClientAuthenticationError

class AzureService:
    def __init__(self):
        self.subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
        try:
            self.credential = DefaultAzureCredential()
            self.compute_client = ComputeManagementClient(self.credential, self.subscription_id)
            self.storage_client = StorageManagementClient(self.credential, self.subscription_id)
            self.resource_client = ResourceManagementClient(self.credential, self.subscription_id)
            self.monitor_client = MonitorManagementClient(self.credential, self.subscription_id)
            self.cost_client = CostManagementClient(self.credential)
        except Exception as e:
            print(f"Azure init error: {e}.")
            self.compute_client = self.storage_client = self.resource_client = self.monitor_client = self.cost_client = None

    def get_resources(self):
        resources = []
        
        # 1. Get VMs
        if self.compute_client:
            try:
                vms = self.compute_client.virtual_machines.list_all()
                for vm in vms:
                    # To get status and ID properly
                    rg_name = vm.id.split('/')[4]
                    status = "Unknown"
                    
                    try:
                        vm_instance = self.compute_client.virtual_machines.instance_view(rg_name, vm.name)
                        for s in vm_instance.statuses:
                            if s.code.startswith('PowerState/'):
                                status = "Running" if s.code == 'PowerState/running' else "Stopped"
                                break
                    except Exception:
                        status = "Running"

                    # Get CPU
                    cpu_usage = 0
                    if status == "Running" and self.monitor_client:
                        try:
                            end_time = datetime.datetime.utcnow()
                            start_time = end_time - datetime.timedelta(minutes=10)
                            timespan = f"{start_time}/{end_time}"
                            
                            metrics = self.monitor_client.metrics.list(
                                vm.id,
                                timespan=timespan,
                                interval='PT5M',
                                metricnames='Percentage CPU',
                                aggregation='Average'
                            )
                            for metric in metrics.value:
                                for timeseries in metric.timeseries:
                                    for data in timeseries.data:
                                        if data.average is not None:
                                            cpu_usage = round(data.average, 1)
                                            break
                        except Exception:
                            pass
                    
                    os_type = "Unknown"
                    if vm.storage_profile and vm.storage_profile.os_disk and vm.storage_profile.os_disk.os_type:
                        os_val = vm.storage_profile.os_disk.os_type
                        os_type = os_val.name if hasattr(os_val, 'name') else str(os_val)

                    size = "Unknown"
                    if vm.hardware_profile and vm.hardware_profile.vm_size:
                        size = vm.hardware_profile.vm_size

                    uptime_str = "0h"

                    resources.append({
                        "id": vm.id,
                        "name": vm.name,
                        "type": "Virtual Machine",
                        "status": status,
                        "region": vm.location,
                        "cpu": cpu_usage,
                        "mem": 0,
                        "cost": 0,
                        "ip": "Unknown", # Requires Network SDK
                        "size": size,
                        "os": os_type,
                        "uptime": uptime_str
                    })
            except Exception as e:
                print(f"Error fetching Azure VMs: {e}")

        # 2. Get Storage Accounts
        if self.storage_client:
            try:
                storage_accounts = self.storage_client.storage_accounts.list()
                for sa in storage_accounts:
                    resources.append({
                        "name": sa.name,
                        "type": "Storage Account",
                        "status": "Running",
                        "region": sa.location,
                        "cpu": 0,
                        "mem": 0,
                        "cost": 0,
                        "ip": "N/A",
                        "size": sa.sku.name if sa.sku else "Standard",
                        "os": "N/A",
                        "uptime": "N/A"
                    })
            except Exception as e:
                print(f"Error fetching Azure Storage Accounts: {e}")

        # 3. Get other resources (Networking, Disks, etc.)
        if self.resource_client:
            try:
                generic_resources = self.resource_client.resources.list()
                for res in generic_resources:
                    res_type = res.type
                    if res_type.lower() not in ['microsoft.compute/virtualmachines', 'microsoft.storage/storageaccounts']:
                        type_name = res_type.split('/')[-1]
                        resources.append({
                            "name": res.name,
                            "type": type_name,
                            "status": "Running",
                            "region": res.location,
                            "cpu": 0,
                            "mem": 0,
                            "cost": 0,
                            "ip": "N/A",
                            "size": "Standard",
                            "os": "N/A",
                            "uptime": "N/A"
                        })
            except Exception as e:
                print(f"Error fetching Azure Generic Resources: {e}")

        return resources

    def start_resource(self, resource_id, resource_type="Virtual Machine"):
        if not self.compute_client:
            return {"status": "error", "message": "Azure client not initialized"}
        if resource_type == "Virtual Machine":
            try:
                # resource_id looks like: /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Compute/virtualMachines/{name}
                parts = resource_id.split('/')
                rg_name = parts[4]
                vm_name = parts[8]
                poller = self.compute_client.virtual_machines.begin_start(rg_name, vm_name)
                # We can return immediately or wait. For API response, we'll just say initiating
                return {"status": "success", "message": f"Initiating start for {vm_name}"}
            except Exception as e:
                return {"status": "error", "message": str(e)}
        return {"status": "error", "message": "Unsupported resource type"}

    def stop_resource(self, resource_id, resource_type="Virtual Machine"):
        if not self.compute_client:
            return {"status": "error", "message": "Azure client not initialized"}
        if resource_type == "Virtual Machine":
            try:
                parts = resource_id.split('/')
                rg_name = parts[4]
                vm_name = parts[8]
                poller = self.compute_client.virtual_machines.begin_deallocate(rg_name, vm_name)
                return {"status": "success", "message": f"Initiating stop for {vm_name}"}
            except Exception as e:
                return {"status": "error", "message": str(e)}
        return {"status": "error", "message": "Unsupported resource type"}

    def get_costs(self):
        empty_data = {
            "cost_months": [],
            "cost_values": [],
            "cost_by_service": {
                "labels": [],
                "values": [],
                "colors": [],
            }
        }
        
        if not self.cost_client:
            return empty_data
            
        try:
            # Azure Cost Management query 
            pass
            return empty_data
        except Exception as e:
            print(f"Error fetching Azure costs: {e}")
            return empty_data
