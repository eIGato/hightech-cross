from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('crosses', '0004_auto_20200511_0723'),
    ]
    operations = [
        migrations.RunSQL('''
            UPDATE crosses_progresslog
            SET details=JSON_BUILD_OBJECT('sn', details->'serial_number')
            WHERE event='GET_PROMPT'; 
        '''),
    ]
