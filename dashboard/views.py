from django.shortcuts import render

def dashboard_view(request):
    
    # Dynamic Data (later replace with Azure API)
    context = {
        "total_vms": 5,
        "running_vms": 3,
        "cost": 1200,
        "storage": 60,

        "resources": [
            {"name": "VM-1", "type": "Virtual Machine", "status": "Running", "region": "India"},
            {"name": "VM-2", "type": "Virtual Machine", "status": "Stopped", "region": "US"},
        ]
    }

    return render(request, 'dashboard/index.html', context)