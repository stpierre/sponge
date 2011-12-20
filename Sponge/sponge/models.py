from django.db import models

class PackageSet(models.Model):
    stype = models.CharField(max_length=16,
                             choices=[('promote', 'Promote'),
                                      ('demote',  'Demote')])


class PackageSetRepo(models.Model):
    packageset = models.ForeignKey(PackageSet)    
    repoid = models.CharField(max_length=255)
    name = models.CharField(max_length=255)


class PackageSetPackage(models.Model):
    packageset = models.ForeignKey(PackageSet)
    packageid = models.CharField(max_length=255)
    pkgobj = models.TextField()


class CeleryTaskTracker(models.Model):
    taskid = models.CharField(max_length=255)
    taskclass = models.CharField(max_length=255)
    owner = models.CharField(max_length=255)
    started = models.DateTimeField(auto_now_add=True)


class Configuration(models.Model):
    name = models.CharField(max_length=255, primary_key=True)
    value = models.CharField(max_length=255)
