from django.db import migrations, models


def backfill_standard_amount(apps, schema_editor):
    """
    Treat the current amount on pre-existing fee lines as their baseline, so any
    future edit is reported as a discount or surcharge against it. Without this
    the adjustment column stays blank for every ledger created before the
    standard_amount field existed.
    """
    PaymentTypeBreakdown = apps.get_model("finance", "PaymentTypeBreakdown")
    PaymentTypeBreakdown.objects.filter(standard_amount__isnull=True).update(
        standard_amount=models.F("amount")
    )


def unset_standard_amount(apps, schema_editor):
    PaymentTypeBreakdown = apps.get_model("finance", "PaymentTypeBreakdown")
    PaymentTypeBreakdown.objects.update(standard_amount=None)


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0002_paymenttypebreakdown_note_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_standard_amount, unset_standard_amount),
    ]
