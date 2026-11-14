from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('accounts', '0001_initial')]
    operations = [
        migrations.AddField(model_name='user', name='phone_verified', field=models.BooleanField(default=False)),
        migrations.CreateModel(name='PhoneOTP', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('phone_number', models.CharField(db_index=True, max_length=11)),
            ('purpose', models.CharField(choices=[('registration','Registration'),('phone_verify','Phone verification')], db_index=True, max_length=30)),
            ('code_hmac', models.CharField(max_length=64)), ('payload', models.JSONField(blank=True, null=True)),
            ('created_at', models.DateTimeField()), ('expires_at', models.DateTimeField()),
            ('consumed_at', models.DateTimeField(blank=True, null=True)), ('superseded_at', models.DateTimeField(blank=True, null=True)),
            ('attempt_count', models.PositiveIntegerField(default=0)),
        ]),
    ]
