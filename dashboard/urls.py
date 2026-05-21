from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    
    # API Routes
    path('api/overview/', views.api_overview, name='api_overview'),
    path('api/resources/', views.api_resources, name='api_resources'),
    path('api/resources/action/', views.api_resource_action, name='api_resource_action'),
    path('api/cost/', views.api_cost, name='api_cost'),
    path('api/alerts/', views.api_alerts, name='api_alerts'),
    path('api/performance/', views.api_performance, name='api_performance'),
    
    # Provider specific
    path('api/aws/ec2/', views.api_aws_ec2, name='api_aws_ec2'),
    path('api/aws/s3/', views.api_aws_s3, name='api_aws_s3'),
    path('api/azure/vms/', views.api_azure_vms, name='api_azure_vms'),
    path('api/azure/storage/', views.api_azure_storage, name='api_azure_storage'),
]