from django.db import migrations

def populate_data(apps, schema_editor):
    Role = apps.get_model('accounts', 'Role')
    Role.objects.create(name="Management")
    Role.objects.create(name="Athlete")

class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),  # ya jo bhi first migration file ka naam ho
    ]

    operations = [
        migrations.RunPython(populate_data),
    ]
