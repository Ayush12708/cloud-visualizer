from rest_framework import serializers
from .models import CloudResource, CostRecord, SecurityAlert

class CloudResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CloudResource
        fields = '__all__'

class CostRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = CostRecord
        fields = '__all__'

class SecurityAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecurityAlert
        fields = '__all__'
