# Migration fantôme — générée sur le Pi, jamais pushée dans git.
# Cette migration a été appliquée sur la DB de prod avant que la migration
# 0005_add_smtp_settings_to_mosquesettings ne soit créée dans le repo.
# On la conserve ici comme stub pour maintenir la cohérence du graphe de migrations.
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_user_permissions_data'),
    ]

    operations = []
