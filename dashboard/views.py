from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
import json
import datetime
from .models import CloudResource, CostRecord, SecurityAlert
from .serializers import CloudResourceSerializer, CostRecordSerializer, SecurityAlertSerializer
from .services.azure_service import AzureService
from .services.aws_service import AWSService

# HTML View
def dashboard_view(request):
    # Pass basic structure; dynamic data will be fetched by React/JS
    return render(request, 'dashboard/index.html')

# API Views
@api_view(['GET'])
def api_overview(request):
    provider = request.GET.get('provider', 'azure').lower()
    
    if provider == 'aws':
        svc = AWSService()
    else:
        svc = AzureService()
        
    resources = svc.get_resources()
    vms = [r for r in resources if r.get('type') in ['Virtual Machine', 'EC2 Instance']]
    storage = [r for r in resources if r.get('type') in ['Storage Account', 'S3 Bucket']]
    
    total_vms = len(vms)
    running_vms = sum(1 for v in vms if v.get('status') == 'Running')
    stopped_vms = total_vms - running_vms
    
    total_cost = sum(r.get('cost', 0) for r in resources)
    
    kpis = {
        "total_vms": total_vms,
        "running_vms": running_vms,
        "stopped_vms": stopped_vms,
        "total_cost": round(total_cost, 2),
        "cost_change": 0,
        "cost_projection": round(total_cost * 1.05, 2) if total_cost else 0,
        "storage_used_gb": sum(r.get('mem', 0) for r in storage),
        "storage_total_gb": 0,
        "storage_pct": 0,
        "network_in_gb": 0,
        "network_out_gb": 0,
        "network_avg_latency_ms": 0,
        "alerts": 0,
        "uptime_pct": 100,
        "avg_iops": 0
    }
    
    return Response(kpis)

@api_view(['GET'])
def api_resources(request):
    provider = request.GET.get('provider', 'azure').lower()
    
    if provider == 'aws':
        aws_service = AWSService()
        resources = aws_service.get_resources()
    else:
        azure_service = AzureService()
        resources = azure_service.get_resources()
        
    return Response(resources)

@api_view(['POST'])
def api_resource_action(request):
    data = request.data
    provider = data.get('provider', 'azure').lower()
    action = data.get('action')
    resource_id = data.get('resource_id')
    resource_type = data.get('resource_type')
    
    if provider == 'aws':
        svc = AWSService()
    else:
        svc = AzureService()
        
    if action == 'start':
        res = svc.start_resource(resource_id, resource_type)
    elif action == 'stop':
        res = svc.stop_resource(resource_id, resource_type)
    else:
        return Response({"status": "error", "message": "Invalid action"}, status=400)
        
    return Response(res)

@api_view(['GET'])
def api_cost(request):
    provider = request.GET.get('provider', 'azure').lower()
    if provider == 'aws':
        svc = AWSService()
    else:
        svc = AzureService()
        
    data = svc.get_costs()
    return Response(data)

@api_view(['GET'])
def api_performance(request):
    provider = request.GET.get('provider', 'azure').lower()
    if provider == 'aws':
        svc = AWSService()
    else:
        svc = AzureService()
        
    if hasattr(svc, 'get_performance'):
        data = svc.get_performance()
    else:
        labels = [(datetime.date.today() - datetime.timedelta(days=i)).strftime('%a') for i in range(6, -1, -1)]
        data = {
            "labels": labels,
            "cpu_data": [],
            "mem_data": []
        }
    return Response(data)

@api_view(['GET'])
def api_alerts(request):
    alerts = []
    return Response(alerts)

# Specific AWS Endpoints
@api_view(['GET'])
def api_aws_ec2(request):
    aws_service = AWSService()
    resources = aws_service.get_resources()
    ec2_resources = [r for r in resources if r.get('type') == 'EC2 Instance']
    return Response(ec2_resources)

@api_view(['GET'])
def api_aws_s3(request):
    aws_service = AWSService()
    resources = aws_service.get_resources()
    s3_resources = [r for r in resources if r.get('type') == 'S3 Bucket']
    return Response(s3_resources)

# Specific Azure Endpoints
@api_view(['GET'])
def api_azure_vms(request):
    azure_service = AzureService()
    resources = azure_service.get_resources()
    vms = [r for r in resources if r.get('type') == 'Virtual Machine']
    return Response(vms)

@api_view(['GET'])
def api_azure_storage(request):
    azure_service = AzureService()
    resources = azure_service.get_resources()
    storage = [r for r in resources if r.get('type') == 'Storage Account']
    return Response(storage)