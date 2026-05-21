from django.db import models

class CloudResource(models.Model):
    PROVIDER_CHOICES = [
        ('azure', 'Azure'),
        ('aws', 'AWS'),
    ]
    
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=100) # e.g. Virtual Machine, SQL Database
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    status = models.CharField(max_length=50) # e.g. Running, Stopped
    region = models.CharField(max_length=100)
    cpu = models.IntegerField(default=0)
    mem = models.IntegerField(default=0)
    cost = models.FloatField(default=0.0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"[{self.provider.upper()}] {self.name} ({self.status})"

class CostRecord(models.Model):
    provider = models.CharField(max_length=20, choices=CloudResource.PROVIDER_CHOICES)
    service_name = models.CharField(max_length=100)
    month = models.CharField(max_length=20) # e.g., '2026-03'
    cost = models.FloatField(default=0.0)
    
    def __str__(self):
        return f"{self.provider.upper()} - {self.service_name} ({self.month}): ${self.cost}"

class SecurityAlert(models.Model):
    LEVEL_CHOICES = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
    ]
    message = models.TextField()
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    provider = models.CharField(max_length=20, choices=CloudResource.PROVIDER_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.level.upper()}] {self.message}"
